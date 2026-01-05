"""
ANSI utilities module for terminal formatting and control sequences.

Provides constants for structural ANSI styles and terminal control sequences,
plus utilities for working with ANSI-escaped text.

Note: Colour-specific codes are user-configurable via tmux config and should not
be hardcoded here. Only structural codes (styles, resets) are defined.
"""

import re


class AnsiStyles:
    """ANSI style and structural codes (not colour-specific)."""

    # Structural styles
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


class TerminalSequences:
    """ANSI terminal control sequence constants."""

    CLEAR_SCREEN = "\033[2J\033[H"


class ControlChars:
    """Terminal control character constants."""

    CTRL_C = "\x03"
    ESC = "\x1b"
    CTRL_U = "\x15"
    CTRL_W = "\x17"
    BACKSPACE = "\x7f"
    BACKSPACE_ALT = "\b"
    ENTER = "\n"
    ENTER_ALT = "\r"


class AnsiUtils:
    """Utilities for working with ANSI-coloured and escape-sequenced text."""

    # Pattern to match ANSI escape sequences
    ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-9;]*m")

    @staticmethod
    def strip_ansi_codes(text: str) -> str:
        """
        Remove ANSI escape codes from text.

        Args:
            text: Text potentially containing ANSI codes

        Returns:
            Text with all ANSI codes removed
        """
        return AnsiUtils.ANSI_ESCAPE_PATTERN.sub("", text)

    @staticmethod
    def map_position_to_coloured(coloured_text: str, plain_pos: int) -> int:
        """
        Map a position in plain text to its position in ANSI-coloured text.

        When text contains ANSI escape codes, the character positions are different
        between the plain version (without codes) and the coloured version (with codes).
        This function finds where a given plain-text position corresponds to in the
        coloured text.

        Args:
            coloured_text: Text containing ANSI colour codes
            plain_pos: Position in the plain (no-codes) version of the text

        Returns:
            The corresponding position in the coloured text
        """
        coloured_idx = 0
        plain_idx = 0

        while plain_idx < plain_pos and coloured_idx < len(coloured_text):
            # Check if we're at the start of an ANSI escape sequence
            if coloured_text[coloured_idx : coloured_idx + 1] == "\x1b":
                # Skip the entire escape sequence
                end = coloured_text.find("m", coloured_idx)
                if end != -1:
                    coloured_idx = end + 1
                else:
                    break
            else:
                # Regular character - advance both indices
                coloured_idx += 1
                plain_idx += 1

        return coloured_idx

    @staticmethod
    def get_visible_length(text: str) -> int:
        """
        Get the visible length of text (excluding ANSI codes).

        Args:
            text: Text potentially containing ANSI codes

        Returns:
            The number of visible characters (not counting ANSI codes)
        """
        return len(AnsiUtils.strip_ansi_codes(text))

    @staticmethod
    def has_ansi_codes(text: str) -> bool:
        """
        Check if text contains any ANSI escape codes.

        Args:
            text: Text to check

        Returns:
            True if text contains ANSI codes, False otherwise
        """
        return bool(AnsiUtils.ANSI_ESCAPE_PATTERN.search(text))
