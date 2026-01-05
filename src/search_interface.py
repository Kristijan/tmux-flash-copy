"""
Search interface module for finding words and generating labels.

This module implements the core search logic similar to flash.nvim,
where search queries are matched against words in the pane content,
and keyboard labels are generated for quick selection.
"""

import re
from collections import defaultdict
from typing import Optional


class SearchMatch:
    """Represents a single matched word with its position and label."""

    def __init__(self, text: str, start_pos: int, end_pos: int, line: int, col: int):
        self.text = text
        self.start_pos = start_pos  # Position in flattened content
        self.end_pos = end_pos
        self.line = line
        self.col = col
        self.label: Optional[str] = None
        self.match_start: int = 0  # Start position of match within the text
        self.match_end: int = 0  # End position of match within the text

    def __repr__(self):
        return (
            f"SearchMatch(text='{self.text}', line={self.line}, col={self.col}, label={self.label})"
        )


class SearchInterface:
    """Manages search queries and label generation."""

    # Default label characters
    DEFAULT_LABELS = "asdfghjklqwertyuiopzxcvbnmASDFGHJKLQWERTYUIOPZXCVBNM"

    # Cache compiled regex patterns
    _pattern_cache: dict[Optional[str], re.Pattern] = {}

    def __init__(
        self,
        pane_content: str,
        reverse_search: bool = True,
        word_separators: Optional[str] = None,
        case_sensitive: bool = False,
    ):
        """
        Initialise the search interface.

        Args:
            pane_content: The full text content of the pane
            reverse_search: If True, prioritize matches from bottom to top (default True)
            word_separators: String of characters to treat as word boundaries.
                           If None, uses default whitespace + punctuation approach.
                           If provided, words are split on these separator characters.
            case_sensitive: If True, search is case-sensitive; if False, case-insensitive (default False)
        """
        self.pane_content = pane_content
        self.lines = pane_content.split("\n")
        self.search_query = ""
        self.matches: list[SearchMatch] = []
        self.reverse_search = reverse_search
        self.word_separators = word_separators
        self.case_sensitive = case_sensitive
        self._build_word_index()

    @classmethod
    def _get_word_pattern(cls, word_separators: Optional[str]) -> re.Pattern:
        """Get or compile word boundary pattern.

        Args:
            word_separators: Word separator characters, or None for default

        Returns:
            Compiled regex pattern
        """
        # Return cached pattern if available
        if word_separators in cls._pattern_cache:
            return cls._pattern_cache[word_separators]

        # Compile new pattern
        if word_separators:
            # Escape for character class
            def escape_for_char_class(s):
                s = s.replace("\\", "\\\\")
                s = s.replace("]", "\\]")
                if s.startswith("^"):
                    s = "^" + s[1:].replace("^", "\\^")
                return s

            escaped = escape_for_char_class(word_separators)
            pattern = re.compile(f"[^{escaped}]+")
        else:
            pattern = re.compile(r"\S+")

        # Cache and return
        cls._pattern_cache[word_separators] = pattern
        return pattern

    def _build_word_index(self):
        """Build an index of all words in the pane content."""
        self.word_index: dict[str, list[SearchMatch]] = defaultdict(list)

        # Get cached or compile word pattern
        word_pattern = self._get_word_pattern(self.word_separators)

        pos = 0
        for line_idx, line in enumerate(self.lines):
            # Split by word boundaries but capture the words
            for match in word_pattern.finditer(line):
                word = match.group()
                word_start = match.start()
                word_end = match.end()

                search_match = SearchMatch(
                    text=word,
                    start_pos=pos + word_start,
                    end_pos=pos + word_end,
                    line=line_idx,
                    col=word_start,
                )
                # Use the word as-is if case-sensitive, or lowercase if case-insensitive
                index_key = word if self.case_sensitive else word.lower()
                self.word_index[index_key].append(search_match)

            pos += len(line) + 1  # +1 for newline

    def search(self, query: str) -> list[SearchMatch]:
        """
        Search for words matching the query.

        Matches words that contain the query string anywhere within them,
        not just at the start. This enables dynamic multi-character search.

        Args:
            query: The search query (can be partial)

        Returns:
            List of SearchMatch objects sorted by position
        """
        # Store the original query, and apply case transformation if needed
        self.search_query = query if self.case_sensitive else query.lower()
        matches_list = []

        if not query:
            self.matches = []
            return []

        # Use the query as-is if case-sensitive, or lowercase if case-insensitive
        search_query = query if self.case_sensitive else query.lower()

        # Find all words that contain the query
        for word, matches_list_from_index in self.word_index.items():
            # Match words that contain the query (anywhere in the word)
            if search_query in word:
                for match in matches_list_from_index:
                    # Find the position of the query within the word
                    if self.case_sensitive:
                        match_pos = match.text.find(search_query)
                    else:
                        match_pos = match.text.lower().find(search_query)

                    if match_pos >= 0:
                        # Create a new match object with match position info
                        new_match = SearchMatch(
                            text=match.text,
                            start_pos=match.start_pos,
                            end_pos=match.end_pos,
                            line=match.line,
                            col=match.col,
                        )
                        new_match.match_start = match_pos
                        new_match.match_end = match_pos + len(search_query)
                        matches_list.append(new_match)

        # Remove duplicates while preserving order
        seen = set()
        unique_matches = []
        for match in matches_list:
            key = (match.start_pos, match.text)
            if key not in seen:
                seen.add(key)
                unique_matches.append(match)

        # Sort by position in content
        unique_matches.sort(key=lambda m: m.start_pos)

        # Reverse sort if reverse_search is enabled (bottom to top)
        if self.reverse_search:
            unique_matches.reverse()

        # Assign labels
        self._assign_labels(unique_matches)

        # Store the unique, labeled matches
        self.matches = unique_matches

        return unique_matches

    def _assign_labels(self, matches: list[SearchMatch]):
        """
        Assign keyboard labels to matches.

        Labels are assigned per-match, where each match excludes:
        1. Characters from the search query (to prevent continuation)
        2. Characters that appear immediately after any match (continuation chars)
        3. Characters from that specific matched word (to avoid ambiguity)
        4. Characters already used by previous matches

        This allows the same label character to be used for different matches
        as long as it doesn't conflict with that specific match.

        Args:
            matches: List of SearchMatch objects to label
        """
        # Get characters to exclude from labels based on search query
        if self.case_sensitive:
            query_chars = set(self.search_query)
        else:
            query_chars = set(self.search_query.lower())

        # Collect characters that appear immediately after matches (continuation chars)
        continuation_chars = set()
        for match in matches:
            # Get the character immediately after the matched portion
            if match.match_end < len(match.text):
                next_char = match.text[match.match_end]
                if self.case_sensitive:
                    continuation_chars.add(next_char)
                else:
                    continuation_chars.add(next_char.lower())

        # Track which labels have been assigned
        used_labels = set()

        # Assign labels to each match
        for match in matches:
            # Get characters from this specific matched word
            match_chars = set(match.text) if self.case_sensitive else set(match.text.lower())

            # Find available labels for this match
            available_labels = []
            for c in self.DEFAULT_LABELS:
                label_lower = c.lower()
                # Skip if already used (check actual character to allow both a and A)
                if c in used_labels:
                    continue
                # Skip if in query, continuation chars, or in this match's text
                if self.case_sensitive:
                    if c in query_chars or c in continuation_chars or c in match_chars:
                        continue
                else:
                    if (
                        label_lower in query_chars
                        or label_lower in continuation_chars
                        or label_lower in match_chars
                    ):
                        continue
                available_labels.append(c)

            # Assign first available label
            if available_labels:
                label = available_labels[0]
                match.label = label
                used_labels.add(label)
            else:
                match.label = None

    def get_match_by_label(self, label: str) -> Optional[SearchMatch]:
        """
        Get a match by its label.

        Args:
            label: The label to search for

        Returns:
            The matching SearchMatch or None
        """
        for match in self.matches:
            if match.label == label:
                return match
        return None

    def get_matches_at_line(self, line_num: int) -> list[SearchMatch]:
        """
        Get all current matches on a specific line.

        Args:
            line_num: The line number

        Returns:
            List of SearchMatch objects on that line
        """
        return [m for m in self.matches if m.line == line_num]
