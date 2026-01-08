"""Tests for search_interface module."""

from src.search_interface import SearchInterface, SearchMatch


class TestSearchMatch:
    """Test SearchMatch dataclass."""

    def test_init(self):
        """Test SearchMatch initialization."""
        match = SearchMatch(text="hello", start_pos=0, end_pos=5, line=0, col=0)

        assert match.text == "hello"
        assert match.start_pos == 0
        assert match.end_pos == 5
        assert match.line == 0
        assert match.col == 0
        assert match.label is None
        assert match.match_start == 0
        assert match.match_end == 0

    def test_repr(self):
        """Test SearchMatch string representation."""
        match = SearchMatch(text="test", start_pos=5, end_pos=9, line=1, col=5)
        match.label = "a"

        repr_str = repr(match)

        assert "SearchMatch" in repr_str
        assert "text='test'" in repr_str
        assert "line=1" in repr_str
        assert "col=5" in repr_str
        assert "label=a" in repr_str


class TestSearchInterface:
    """Test SearchInterface functionality."""

    def test_init_basic(self):
        """Test SearchInterface initialization."""
        content = "hello world\nfoo bar"
        search = SearchInterface(content)

        assert search.pane_content == content
        assert search.lines == ["hello world", "foo bar"]
        assert search.search_query == ""
        assert search.matches == []
        assert search.reverse_search is True
        assert search.word_separators is None
        assert search.case_sensitive is False

    def test_init_with_options(self):
        """Test SearchInterface initialization with custom options."""
        content = "test"
        search = SearchInterface(
            content, reverse_search=False, word_separators=" -", case_sensitive=True
        )

        assert search.reverse_search is False
        assert search.word_separators == " -"
        assert search.case_sensitive is True

    def test_word_index_built_on_init(self):
        """Test that word index is built on initialization."""
        content = "hello world hello"
        search = SearchInterface(content)

        # Word index should be populated
        assert len(search.word_index) > 0
        assert "hello" in search.word_index
        assert "world" in search.word_index

    def test_search_empty_query(self):
        """Test search with empty query."""
        content = "hello world"
        search = SearchInterface(content)

        matches = search.search("")

        assert len(matches) == 0
        assert search.matches == []

    def test_search_single_match(self):
        """Test search with single match."""
        content = "hello world"
        search = SearchInterface(content)

        matches = search.search("world")

        assert len(matches) == 1
        assert matches[0].text == "world"
        assert matches[0].line == 0
        assert matches[0].col == 6

    def test_search_multiple_matches(self):
        """Test search with multiple matches."""
        content = "hello world\nhello there"
        search = SearchInterface(content)

        matches = search.search("hello")

        assert len(matches) == 2
        assert all(m.text == "hello" for m in matches)

    def test_search_partial_match(self):
        """Test search with partial word match."""
        content = "testing test tests"
        search = SearchInterface(content)

        matches = search.search("test")

        assert len(matches) == 3
        # All three words should be matched
        match_texts = {m.text for m in matches}
        assert match_texts == {"testing", "test", "tests"}

    def test_search_case_insensitive(self):
        """Test case-insensitive search (default)."""
        content = "Hello HELLO hello"
        search = SearchInterface(content, case_sensitive=False)

        matches = search.search("hello")

        assert len(matches) == 3

    def test_search_case_sensitive(self):
        """Test case-sensitive search."""
        content = "Hello HELLO hello"
        search = SearchInterface(content, case_sensitive=True)

        matches = search.search("hello")

        assert len(matches) == 1
        assert matches[0].text == "hello"

    def test_search_with_custom_separators(self):
        """Test search with custom word separators."""
        content = "foo-bar foo_bar"
        search = SearchInterface(content, word_separators=" -")

        matches = search.search("bar")

        # With " -" as separators, we match non-whitespace sequences
        # and extract words based on separators for copying
        assert len(matches) == 2
        # Match 1: sequence "foo-bar", copy_text "bar" (dash is separator)
        assert any(m.text == "foo-bar" and m.copy_text == "bar" for m in matches)
        # Match 2: sequence "foo_bar", copy_text "foo_bar" (underscore not a separator)
        assert any(m.text == "foo_bar" and m.copy_text == "foo_bar" for m in matches)

    def test_search_reverse_order(self):
        """Test search with reverse ordering (bottom to top)."""
        content = "line1 word\nline2 word\nline3 word"
        search = SearchInterface(content, reverse_search=True)

        matches = search.search("word")

        # Should be ordered from bottom to top
        assert matches[0].line == 2
        assert matches[1].line == 1
        assert matches[2].line == 0

    def test_search_forward_order(self):
        """Test search with forward ordering (top to bottom)."""
        content = "line1 word\nline2 word\nline3 word"
        search = SearchInterface(content, reverse_search=False)

        matches = search.search("word")

        # Should be ordered from top to bottom
        assert matches[0].line == 0
        assert matches[1].line == 1
        assert matches[2].line == 2

    def test_search_match_positions(self):
        """Test that match positions are recorded correctly."""
        content = "testing test"
        search = SearchInterface(content)

        matches = search.search("test")

        # First match "testing" contains "test" at position 0
        assert matches[0].match_start == 0
        assert matches[0].match_end == 4

        # Second match "test" contains "test" at position 0
        assert matches[1].match_start == 0
        assert matches[1].match_end == 4

    def test_label_assignment(self):
        """Test that labels are assigned to matches."""
        content = "foo bar baz"
        search = SearchInterface(content)

        matches = search.search("b")

        # Both matches should get labels
        assert matches[0].label is not None
        assert matches[1].label is not None
        # Labels should be different
        assert matches[0].label != matches[1].label

    def test_label_excludes_query_chars(self):
        """Test that labels don't include query characters."""
        content = "apple banana cherry"
        search = SearchInterface(content)

        matches = search.search("a")

        # Labels should not include 'a' (case-insensitive)
        for match in matches:
            if match.label:
                assert match.label.lower() != "a"

    def test_label_excludes_match_chars(self):
        """Test that labels don't include characters from matched word."""
        content = "foo bar"
        search = SearchInterface(content)

        matches = search.search("f")

        # Label for "foo" should not include 'f' or 'o'
        match = matches[0]
        if match.label:
            assert match.label.lower() not in ["f", "o"]

    def test_get_match_by_label(self):
        """Test getting match by label."""
        content = "foo bar baz"
        search = SearchInterface(content)

        search.search("b")

        # Get the first match's label
        first_label = search.matches[0].label
        assert first_label is not None  # Ensure label was assigned

        # Should be able to retrieve it
        match = search.get_match_by_label(first_label)
        assert match is not None
        assert match.label == first_label

    def test_get_match_by_label_not_found(self):
        """Test getting match by non-existent label."""
        content = "foo bar"
        search = SearchInterface(content)

        search.search("foo")

        match = search.get_match_by_label("Z")

        assert match is None

    def test_get_matches_at_line(self):
        """Test getting matches at specific line."""
        content = "foo bar\nbaz foo\nbar baz"
        search = SearchInterface(content)

        search.search("ba")

        # Line 0 should have "bar"
        matches_line_0 = search.get_matches_at_line(0)
        assert len(matches_line_0) == 1
        assert matches_line_0[0].text == "bar"

        # Line 1 should have "baz"
        matches_line_1 = search.get_matches_at_line(1)
        assert len(matches_line_1) == 1
        assert matches_line_1[0].text == "baz"

        # Line 2 should have both "bar" and "baz"
        matches_line_2 = search.get_matches_at_line(2)
        assert len(matches_line_2) == 2

    def test_get_matches_at_line_no_matches(self):
        """Test getting matches at line with no matches."""
        content = "foo bar\nbaz"
        search = SearchInterface(content)

        search.search("foo")

        matches = search.get_matches_at_line(1)

        assert len(matches) == 0

    def test_search_preserves_match_text_case(self):
        """Test that match text preserves original case."""
        content = "Hello World"
        search = SearchInterface(content, case_sensitive=False)

        matches = search.search("hello")

        assert matches[0].text == "Hello"  # Original case preserved

    def test_deduplicate_matches(self):
        """Test that duplicate matches are removed."""
        content = "test test"
        search = SearchInterface(content)

        matches = search.search("test")

        # Should have 2 matches (one for each "test")
        assert len(matches) == 2
        # But they should be at different positions
        assert matches[0].start_pos != matches[1].start_pos

    def test_multiline_search(self):
        """Test search across multiple lines."""
        content = "line one\nline two\nline three"
        search = SearchInterface(content)

        matches = search.search("line")

        assert len(matches) == 3
        assert matches[0].line != matches[1].line != matches[2].line

    def test_search_with_punctuation(self):
        """Test search with words containing punctuation."""
        content = "test! test? test."
        search = SearchInterface(content)

        matches = search.search("test")

        # All three should match
        assert len(matches) == 3

    def test_empty_content(self):
        """Test search with empty content."""
        search = SearchInterface("")

        matches = search.search("test")

        assert len(matches) == 0

    def test_single_word_content(self):
        """Test search with single word content."""
        search = SearchInterface("hello")

        matches = search.search("hello")

        assert len(matches) == 1
        assert matches[0].text == "hello"

    def test_word_pattern_caching(self):
        """Test that word patterns are cached."""
        # Create two instances with same separator config to populate cache
        SearchInterface("test", word_separators=" -")
        SearchInterface("test", word_separators=" -")

        # They should use the same cached pattern
        pattern1 = SearchInterface._get_word_pattern(" -")
        pattern2 = SearchInterface._get_word_pattern(" -")

        assert pattern1 is pattern2

    def test_get_word_pattern_escape_starting_caret(self):
        """Ensure _get_word_pattern handles separators starting with '^'."""
        # This exercises the escape_for_char_class branch where s.startswith("^")
        pattern = SearchInterface._get_word_pattern("^")

        assert hasattr(pattern, "findall")

        # With '^' as a separator the pattern should split on '^'
        text = "a^b^c"
        parts = pattern.findall(text)
        # Should find the segments between '^' characters
        assert parts == ["a", "b", "c"]

    def test_word_separators_only_whitespace(self):
        """When `word_separators` contains only whitespace, no leading non-ws separators are captured."""
        content = "hello world"
        # Only a space character as separator -> non_ws_seps becomes empty -> separator_pattern = None
        search = SearchInterface(content, word_separators=" ")

        # Words should be parsed normally without any leading separator characters
        matches = search.search("world")
        assert len(matches) == 1
        assert matches[0].text == "world"

    def test_label_assignment_exhaustion(self):
        """Test label assignment when running out of available labels."""
        # Create content with many words that use up most labels
        words = [f"word{i}" for i in range(100)]
        content = " ".join(words)
        search = SearchInterface(content)

        matches = search.search("word")

        # Some matches should have labels, some might not (exhausted)
        labeled = [m for m in matches if m.label is not None]
        assert len(labeled) > 0  # At least some should be labeled

    def test_continuation_chars_excluded_from_labels(self):
        """Test that continuation characters are excluded from labels."""
        content = "testing test"
        search = SearchInterface(content)

        matches = search.search("test")

        # For "testing", continuation char after "test" is "i"
        # Labels should not include 'i'
        for match in matches:
            if match.label:
                assert match.label.lower() != "i"

    def test_search_updates_query(self):
        """Test that search updates the search_query attribute."""
        content = "hello world"
        search = SearchInterface(content)

        search.search("hello")

        assert search.search_query == "hello"

    def test_search_updates_matches(self):
        """Test that search updates the matches attribute."""
        content = "hello world"
        search = SearchInterface(content)

        # Initial matches should be empty
        assert search.matches == []

        search.search("hello")

        # Matches should be populated
        assert len(search.matches) > 0

    def test_search_without_word_separators(self):
        """Test search without word separators uses default pattern."""
        # Clear cache to ensure pattern compilation path is hit
        SearchInterface._pattern_cache.clear()

        content = "hello-world foo_bar"
        # No word_separators specified
        search = SearchInterface(content, word_separators=None)

        matches = search.search("world")

        # Should find "hello-world" as one sequence
        assert len(matches) == 1
        assert matches[0].text == "hello-world"

    def test_search_match_in_separators_only(self):
        """Test when match is in separators only, copy first word after match."""
        content = "a#longer#c"
        separators = "#"
        search = SearchInterface(content, word_separators=separators)

        matches = search.search("#")

        # Match is the # character, should copy the word after each match
        assert len(matches) == 2
        # First # at position 1, next word is 'longer'
        # Second # at position 8, next word is 'c'
        # Results are sorted, so order depends on reverse_search
        copy_texts = sorted([m.copy_text for m in matches])
        assert copy_texts == ["c", "longer"]

    def test_search_match_fallback_to_longest_word(self):
        """Test when match is at end with no following word, fallback to longest."""
        content = "a#longer#"
        separators = "#"
        search = SearchInterface(content, word_separators=separators)

        matches = search.search("#")

        # Both # characters have no word after them (or reach end of sequence)
        # Should fall back to longest word in sequence
        assert len(matches) == 2
        # Should pick 'longer' (longest word) for both
        assert all(m.copy_text == "longer" for m in matches)

    def test_label_assignment_case_sensitive_continuation(self):
        """Test label assignment with case-sensitive continuation chars."""
        content = "Hello World"
        search = SearchInterface(content, case_sensitive=True)

        matches = search.search("H")

        # In case-sensitive mode, continuation char 'e' should be excluded
        assert len(matches) == 1
        # Label should not be 'e' (continuation char after 'H')
        if matches[0].label:
            assert matches[0].label != "e"
