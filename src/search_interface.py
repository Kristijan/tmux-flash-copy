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

    def __init__(
        self,
        text: str,
        start_pos: int,
        end_pos: int,
        line: int,
        col: int,
        copy_text: Optional[str] = None,
    ):
        self.text = text  # Extended text including separators for matching
        self.start_pos = start_pos  # Position in flattened content
        self.end_pos = end_pos
        self.line = line
        self.col = col
        self.label: Optional[str] = None
        self.match_start: int = 0  # Start position of match within the text
        self.match_end: int = 0  # End position of match within the text
        # The actual word to copy (without leading/trailing separators)
        self.copy_text: str = copy_text if copy_text is not None else text

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

    @staticmethod
    def _escape_for_char_class(s: str) -> str:
        """Escape special characters for use in regex character class."""
        s = s.replace("\\", "\\\\")
        s = s.replace("]", "\\]")
        if s.startswith("^"):
            s = "^" + s[1:].replace("^", "\\^")
        return s

    def __init__(
        self,
        pane_content: str,
        reverse_search: bool = True,
        word_separators: Optional[str] = None,
        case_sensitive: bool = False,
        label_characters: Optional[str] = None,
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
        # Label characters can be customised per-instance; fall back to class default
        self.label_characters = label_characters if label_characters else self.DEFAULT_LABELS
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
            escaped = cls._escape_for_char_class(word_separators)
            pattern = re.compile(f"[^{escaped}]+")
        else:
            pattern = re.compile(r"\S+")

        # Cache and return
        cls._pattern_cache[word_separators] = pattern
        return pattern

    def _build_word_index(self):
        """Build an index of all non-whitespace sequences in the pane content.

        Per CLAUDE.md: Word separators only apply to what is copied, not searching.
        We match all non-whitespace sequences for searching, and extract the word
        part (using separators) for copying.
        """
        self.word_index: dict[str, list[SearchMatch]] = defaultdict(list)

        # Always match non-whitespace sequences for searching
        sequence_pattern = re.compile(r"\S+")

        # Compile word pattern for extracting copy text
        if self.word_separators:
            escaped = self._escape_for_char_class(self.word_separators)
            word_pattern = re.compile(f"[^{escaped}]+")
        else:
            word_pattern = None

        pos = 0
        for line_idx, line in enumerate(self.lines):
            # Find all non-whitespace sequences
            for match in sequence_pattern.finditer(line):
                sequence = match.group()
                sequence_start = match.start()
                sequence_end = match.end()

                # Extract the word to copy from this sequence using separators
                copy_text: str = sequence  # Default to full sequence
                if word_pattern:
                    # Find all words within the sequence
                    words = word_pattern.findall(sequence)
                    if words:
                        # Use the longest word as copy text
                        copy_text = str(max(words, key=len))

                search_match = SearchMatch(
                    text=sequence,
                    start_pos=pos + sequence_start,
                    end_pos=pos + sequence_end,
                    line=line_idx,
                    col=sequence_start,
                    copy_text=copy_text,
                )
                # Use the sequence for indexing (case-sensitive or lowercase)
                index_key = sequence if self.case_sensitive else sequence.lower()
                self.word_index[index_key].append(search_match)

            pos += len(line) + 1  # +1 for newline

    def search(self, query: str) -> list[SearchMatch]:
        """
        Search for words matching the query.

        Finds all occurrences of the query string, potentially multiple times
        within the same sequence. For each occurrence, determines the word to copy.

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

        # Compile word pattern for extracting copy text
        if self.word_separators:
            escaped = self._escape_for_char_class(self.word_separators)
            word_pattern = re.compile(f"[^{escaped}]+")
        else:
            word_pattern = None

        # Find all sequences that contain the query
        for sequence_key, matches_from_index in self.word_index.items():
            # Check if this sequence contains the query
            if search_query in sequence_key:
                for sequence_match in matches_from_index:
                    # Find ALL occurrences of the query in this sequence
                    search_text = (
                        sequence_match.text if self.case_sensitive else sequence_match.text.lower()
                    )
                    match_pos = 0
                    while True:
                        match_pos = search_text.find(search_query, match_pos)
                        if match_pos < 0:
                            break

                        # Determine which word to copy for this match occurrence
                        copy_text: str = sequence_match.text  # Default to full sequence
                        if word_pattern:
                            # Find the word that contains or follows this match
                            best_word: Optional[str] = None
                            for word_match in word_pattern.finditer(sequence_match.text):
                                word_start = word_match.start()
                                word_end = word_match.end()
                                # Check if match falls within this word
                                if (
                                    word_start <= match_pos < word_end
                                    or word_start > match_pos
                                    and best_word is None
                                ):
                                    best_word = word_match.group()
                                    break

                            if best_word:
                                copy_text = best_word
                            else:
                                # No word found, use the longest word in sequence
                                words = word_pattern.findall(sequence_match.text)
                                if words:
                                    copy_text = str(max(words, key=len))

                        # Create a new match object for this occurrence
                        new_match = SearchMatch(
                            text=sequence_match.text,
                            start_pos=sequence_match.start_pos,
                            end_pos=sequence_match.end_pos,
                            line=sequence_match.line,
                            col=sequence_match.col,
                            copy_text=copy_text,
                        )
                        new_match.match_start = match_pos
                        new_match.match_end = match_pos + len(search_query)
                        matches_list.append(new_match)

                        # Move to next position
                        match_pos += 1

        # Remove duplicates while preserving order
        seen = set()
        unique_matches = []
        for match in matches_list:
            key = (match.start_pos, match.match_start, match.text)
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
            for c in self.label_characters:
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
