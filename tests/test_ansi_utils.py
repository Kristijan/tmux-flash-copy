"""Tests for ansi_utils module."""

from src.ansi_utils import AnsiStyles, AnsiUtils, ControlChars, TerminalSequences


class TestAnsiStyles:
    """Test ANSI style constants."""

    def test_bold_constant(self):
        """Test BOLD constant value."""
        assert AnsiStyles.BOLD == "\033[1m"

    def test_dim_constant(self):
        """Test DIM constant value."""
        assert AnsiStyles.DIM == "\033[2m"

    def test_reset_constant(self):
        """Test RESET constant value."""
        assert AnsiStyles.RESET == "\033[0m"


class TestTerminalSequences:
    """Test terminal sequence constants."""

    def test_clear_screen_constant(self):
        """Test CLEAR_SCREEN constant value."""
        assert TerminalSequences.CLEAR_SCREEN == "\033[2J\033[H"


class TestControlChars:
    """Test control character constants."""

    def test_ctrl_c_constant(self):
        """Test CTRL_C constant value."""
        assert ControlChars.CTRL_C == "\x03"

    def test_esc_constant(self):
        """Test ESC constant value."""
        assert ControlChars.ESC == "\x1b"

    def test_ctrl_u_constant(self):
        """Test CTRL_U constant value."""
        assert ControlChars.CTRL_U == "\x15"

    def test_ctrl_w_constant(self):
        """Test CTRL_W constant value."""
        assert ControlChars.CTRL_W == "\x17"

    def test_backspace_constant(self):
        """Test BACKSPACE constant value."""
        assert ControlChars.BACKSPACE == "\x7f"

    def test_backspace_alt_constant(self):
        """Test BACKSPACE_ALT constant value."""
        assert ControlChars.BACKSPACE_ALT == "\b"

    def test_enter_constant(self):
        """Test ENTER constant value."""
        assert ControlChars.ENTER == "\n"

    def test_enter_alt_constant(self):
        """Test ENTER_ALT constant value."""
        assert ControlChars.ENTER_ALT == "\r"


class TestAnsiUtils:
    """Test AnsiUtils functionality."""

    def test_strip_ansi_codes_with_no_codes(self):
        """Test stripping ANSI codes from text without codes."""
        text = "Hello, World!"
        result = AnsiUtils.strip_ansi_codes(text)
        assert result == "Hello, World!"

    def test_strip_ansi_codes_with_single_code(self):
        """Test stripping ANSI codes from text with a single code."""
        text = "\033[1mBold Text\033[0m"
        result = AnsiUtils.strip_ansi_codes(text)
        assert result == "Bold Text"

    def test_strip_ansi_codes_with_multiple_codes(self):
        """Test stripping ANSI codes from text with multiple codes."""
        text = "\033[1;31mRed Bold\033[0m and \033[32mGreen\033[0m"
        result = AnsiUtils.strip_ansi_codes(text)
        assert result == "Red Bold and Green"

    def test_strip_ansi_codes_with_empty_string(self):
        """Test stripping ANSI codes from empty string."""
        text = ""
        result = AnsiUtils.strip_ansi_codes(text)
        assert result == ""

    def test_strip_ansi_codes_with_only_codes(self):
        """Test stripping ANSI codes from string with only codes."""
        text = "\033[1m\033[31m\033[0m"
        result = AnsiUtils.strip_ansi_codes(text)
        assert result == ""

    def test_get_visible_length_plain_text(self):
        """Test visible length of plain text."""
        text = "Hello"
        assert AnsiUtils.get_visible_length(text) == 5

    def test_get_visible_length_with_ansi_codes(self):
        """Test visible length of text with ANSI codes."""
        text = "\033[1mHello\033[0m"
        assert AnsiUtils.get_visible_length(text) == 5

    def test_get_visible_length_empty_string(self):
        """Test visible length of empty string."""
        text = ""
        assert AnsiUtils.get_visible_length(text) == 0

    def test_get_visible_length_complex_formatting(self):
        """Test visible length with complex ANSI formatting."""
        text = "\033[1;31mRed\033[0m \033[32mGreen\033[0m"
        assert AnsiUtils.get_visible_length(text) == 9  # "Red Green"

    def test_has_ansi_codes_with_codes(self):
        """Test detection of ANSI codes in text with codes."""
        text = "\033[1mBold\033[0m"
        assert AnsiUtils.has_ansi_codes(text) is True

    def test_has_ansi_codes_without_codes(self):
        """Test detection of ANSI codes in plain text."""
        text = "Plain text"
        assert AnsiUtils.has_ansi_codes(text) is False

    def test_has_ansi_codes_empty_string(self):
        """Test detection of ANSI codes in empty string."""
        text = ""
        assert AnsiUtils.has_ansi_codes(text) is False

    def test_map_position_to_coloured_no_codes(self):
        """Test mapping position in plain text without ANSI codes."""
        text = "Hello"
        assert AnsiUtils.map_position_to_coloured(text, 0) == 0
        assert AnsiUtils.map_position_to_coloured(text, 2) == 2
        assert AnsiUtils.map_position_to_coloured(text, 5) == 5

    def test_map_position_to_coloured_with_codes_at_start(self):
        """Test mapping position with ANSI codes at the start."""
        text = "\033[1mHello\033[0m"
        # Position 0 in plain text maps to position 0 in coloured text
        assert AnsiUtils.map_position_to_coloured(text, 0) == 0
        # Position 1 in plain text ('e') is after skipping "\033[1m" and 'H'
        assert AnsiUtils.map_position_to_coloured(text, 1) == 5  # After "\033[1m" + 'H'

    def test_map_position_to_coloured_with_codes_in_middle(self):
        """Test mapping position with ANSI codes in the middle."""
        text = "Hi\033[1mBold\033[0m"
        # Position 0 should be 0 (before codes)
        assert AnsiUtils.map_position_to_coloured(text, 0) == 0
        # Position 2 should be 2 (before codes)
        assert AnsiUtils.map_position_to_coloured(text, 2) == 2
        # Position 3 should be after "Hi" and "\033[1m" and 'B'
        assert AnsiUtils.map_position_to_coloured(text, 3) == 7  # 2 + 4 (code) + 1 ('B')

    def test_map_position_to_coloured_with_multiple_codes(self):
        """Test mapping position with multiple ANSI codes."""
        text = "\033[31mR\033[0m\033[32mG\033[0m"
        # First visible char 'R' is at plain position 0
        assert AnsiUtils.map_position_to_coloured(text, 0) == 0
        # Position 1 in plain text is after "\033[31m" (5) + "R" (1)
        assert AnsiUtils.map_position_to_coloured(text, 1) == 6

    def test_map_position_to_coloured_beyond_text_length(self):
        """Test mapping position beyond text length."""
        text = "\033[1mHi\033[0m"
        # Position beyond the plain text should return the length of coloured text
        result = AnsiUtils.map_position_to_coloured(text, 10)
        # Should stop at the end of the string
        assert result <= len(text)

    def test_map_position_to_coloured_empty_string(self):
        """Test mapping position in empty string."""
        text = ""
        assert AnsiUtils.map_position_to_coloured(text, 0) == 0
