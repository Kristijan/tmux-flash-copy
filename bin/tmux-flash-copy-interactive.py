#!/usr/bin/env python3
"""
Interactive search UI that runs inside the tmux popup/window.

This script manages the terminal UI for searching, displaying matches,
and handling user input for label selection.
"""

import argparse
import os
import shutil
import sys
import termios
import tty
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
PLUGIN_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PLUGIN_DIR))

from src.ansi_utils import AnsiStyles, AnsiUtils, ControlChars, TerminalSequences  # noqa: E402
from src.clipboard import Clipboard  # noqa: E402
from src.config import FlashCopyConfig  # noqa: E402
from src.debug_logger import DebugLogger  # noqa: E402
from src.pane_capture import PaneCapture  # noqa: E402
from src.search_interface import SearchInterface  # noqa: E402


class InteractiveUI:
    """Manages the interactive search UI in the terminal."""

    def __init__(
        self,
        pane_id: str,
        temp_dir: str,
        pane_content: str,
        dimensions: dict,
        config: FlashCopyConfig,
    ):
        """
        Initialise the interactive UI.

        Args:
            pane_id: The tmux pane ID
            temp_dir: Temporary directory for state files
            pane_content: The captured pane content
            dimensions: Pane dimensions dict
            config: FlashCopyConfig with all configuration options
        """
        self.pane_id = pane_id
        self.temp_dir = temp_dir
        self.pane_content = pane_content
        # Strip ANSI codes for searching
        self.pane_content_plain = AnsiUtils.strip_ansi_codes(pane_content)
        self.dimensions = dimensions
        self.config = config
        # Use plain text for searching
        self.search_interface = SearchInterface(
            self.pane_content_plain,
            reverse_search=config.reverse_search,
            word_separators=config.word_separators,
            case_sensitive=config.case_sensitive,
            label_characters=config.label_characters,
        )
        self.clipboard = Clipboard()
        self.search_query = ""
        self.current_matches = []
        self.autopaste_modifier_active = False
        self.last_logged_modifier = None  # Track last logged modifier state to avoid repetition
        # Initialize debug logger if enabled
        self.debug_logger = (
            DebugLogger.get_instance()
            if hasattr(config, "debug_enabled") and config.debug_enabled
            else None
        )

    def _update_search(self, new_query: str):
        """
        Update search query and refresh the display.

        This is a convenience method that handles the common pattern of:
        1. Updating the search query
        2. Running the search
        3. Refreshing the display

        Args:
            new_query: The new search query string
        """
        self.search_query = new_query
        self.current_matches = self.search_interface.search(self.search_query)

        # Log search query and results
        if self.debug_logger and self.debug_logger.enabled:
            self.debug_logger.log(
                f"Search query: '{new_query}' -> {len(self.current_matches)} matches"
            )
            if self.current_matches:
                # Log first 10 matches
                for _i, match in enumerate(self.current_matches[:10]):
                    self.debug_logger.log(
                        f"  [{match.label or '?'}] line {match.line}, col {match.col}: '{match.text}'"
                    )
                if len(self.current_matches) > 10:
                    self.debug_logger.log(
                        f"  ... and {len(self.current_matches) - 10} more matches"
                    )

        self._display_content()

    def _get_single_char(self) -> str:
        """
        Read a single character or escape sequence from stdin without waiting for Enter.

        Returns:
            The character or special value read, or empty string on EOF
        """
        try:
            fd = sys.stdin.fileno()
            # Check if stdin is a TTY before attempting to set raw mode
            if not os.isatty(fd):
                # If not a TTY (e.g., in a tmux popup), read one character directly
                # This will block until input is available
                char = sys.stdin.read(1)
                if not char:  # EOF
                    return ControlChars.CTRL_C  # Treat EOF as Ctrl+C
                # Check for escape sequences
                if char == ControlChars.ESC:
                    return self._handle_escape_sequence()
                return char

            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                char = sys.stdin.read(1)
                if not char:  # EOF
                    return ControlChars.CTRL_C  # Treat EOF as Ctrl+C
                # Check for escape sequences
                if char == ControlChars.ESC:
                    return self._handle_escape_sequence()
                return char
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        except Exception as e:
            print(f"Error reading input: {e}", file=sys.stderr)
            return ControlChars.CTRL_C  # Treat any error as Ctrl+C

    def _handle_escape_sequence(self) -> str:
        """
        Handle ESC key press.

        Returns:
            ControlChars.ESC to cancel, or empty string to ignore
        """
        # If autopaste modifier is active, ignore ESC
        # (prevents accidental cancellation while using modifier)
        if self.autopaste_modifier_active:
            if self.debug_logger and self.debug_logger.enabled:
                self.debug_logger.log("Ignoring ESC while autopaste modifier active")
            return ""  # Ignore when modifier is active
        return ControlChars.ESC

    def _clear_screen(self):
        """Clear the terminal screen."""
        sys.stdout.write(TerminalSequences.CLEAR_SCREEN)
        sys.stdout.flush()

    def _reset_terminal(self):
        """Reset terminal state (scrolling region, etc.)."""
        # Reset scrolling region to full screen (ANSI: \033[r)
        sys.stdout.write("\033[r")
        sys.stdout.flush()

    def _dim_coloured_line(self, line: str) -> str:
        """Apply dimming to a line with ANSI colour codes.

        Reapplies dimming after each colour reset to darken coloured content.
        """
        # After each reset code, reapply the dim code
        dimmed = line.replace(AnsiStyles.RESET, AnsiStyles.RESET + AnsiStyles.DIM)
        # Start with dim at the beginning
        if not dimmed.startswith(AnsiStyles.DIM):
            dimmed = AnsiStyles.DIM + dimmed
        # Ensure it ends with reset
        if not dimmed.endswith(AnsiStyles.RESET):
            dimmed = dimmed + AnsiStyles.RESET
        return dimmed

    def _build_search_bar_output(self) -> str:
        """
        Build the search bar output string with optional debug indicator.

        Returns:
            The formatted search bar with prompt, query or placeholder text, and debug indicator if enabled
        """
        # Build base prompt
        if self.search_query:
            base_output = (
                f"{self.config.prompt_colour}{self.config.prompt_indicator}{AnsiStyles.RESET} "
                + self.search_query
            )
        elif self.config.prompt_placeholder_text:
            base_output = (
                f"{self.config.prompt_colour}{self.config.prompt_indicator}{AnsiStyles.RESET} {AnsiStyles.DIM}"
                + self.config.prompt_placeholder_text
                + AnsiStyles.RESET
            )
        else:
            base_output = (
                f"{self.config.prompt_colour}{self.config.prompt_indicator}{AnsiStyles.RESET} "
            )

        # Add debug indicator if enabled (right-aligned)
        if self.debug_logger and self.debug_logger.enabled:
            try:
                term_width = shutil.get_terminal_size().columns
            except OSError:
                term_width = 80

            debug_text = "!! DEBUG ON !!"
            base_visible_len = AnsiUtils.get_visible_length(base_output)
            debug_visible_len = len(debug_text)

            # Only add if there's enough space (at least 3 chars padding between prompt and debug text)
            if base_visible_len + debug_visible_len + 3 < term_width:
                padding = term_width - base_visible_len - debug_visible_len - 1
                base_output += " " * padding + f"{AnsiStyles.DIM}{debug_text}{AnsiStyles.RESET}"

        return base_output

    def _display_line_with_matches(self, display_line: str, line_idx: int, line_plain: str) -> str:
        """
        Process and format a line that contains matches.

        Applies highlighting to matched text and adds match labels. The function
        accepts the plain (ANSI-stripped) version of the line as ``line_plain``
        so it can inspect raw characters (for example, to detect a single space
        following a matched word and overwrite it with the label instead of
        inserting a character that would shift the line).

        Args:
            display_line: The line content including ANSI escape codes.
            line_idx: The line index in the pane content.
            line_plain: The same line with ANSI codes removed (plain characters).

        Returns:
            The coloured line with highlights and labels applied. If a space
            follows a matched word, the label will replace that space to avoid
            changing visible layout.
        """
        matches_on_line = self.search_interface.get_matches_at_line(line_idx)

        # Process matches from right to left to maintain position accuracy
        for match in sorted(matches_on_line, key=lambda m: m.col, reverse=True):
            if not match.label:
                continue

            # Get the matched word and its position
            word_start = match.col
            match_start_in_word = match.match_start
            match_end_in_word = match.match_end

            # Find positions in coloured line using AnsiUtils
            coloured_word_start = AnsiUtils.map_position_to_coloured(display_line, word_start)
            coloured_match_start_in_word = AnsiUtils.map_position_to_coloured(
                display_line[coloured_word_start:], match_start_in_word
            )

            # We'll place the label by replacing (or inserting) the single plain
            # character immediately after the matched substring, then apply
            # highlighting to the matched substring. Doing the single-character
            # replacement first keeps index calculations simpler (we're
            # processing right-to-left so changes to the right won't affect
            # earlier positions).

            # Compute the plain index of the character to replace (immediately
            # after the matched substring)
            plain_replace_index = word_start + match_end_in_word

            # Insert or replace the single plain character with the coloured label
            if plain_replace_index < len(line_plain):
                coloured_replace_start = AnsiUtils.map_position_to_coloured(
                    display_line, plain_replace_index
                )
                # How many bytes in the coloured string correspond to one plain char
                coloured_skip_len = AnsiUtils.map_position_to_coloured(
                    display_line[coloured_replace_start:], 1
                )
                # Replace that single plain character with the coloured label
                coloured_label = f"{self.config.label_colour}{match.label}{AnsiStyles.RESET}"
                display_line = (
                    display_line[:coloured_replace_start]
                    + coloured_label
                    + display_line[coloured_replace_start + coloured_skip_len :]
                )
            else:
                # No character to replace (end of line) — insert label after match
                coloured_insert_pos = AnsiUtils.map_position_to_coloured(
                    display_line, plain_replace_index
                )
                coloured_label = f"{self.config.label_colour}{match.label}{AnsiStyles.RESET}"
                display_line = (
                    display_line[:coloured_insert_pos]
                    + coloured_label
                    + display_line[coloured_insert_pos:]
                )

            # Recompute coloured positions after the label insertion/replacement
            coloured_word_start = AnsiUtils.map_position_to_coloured(display_line, word_start)
            coloured_match_start_in_word = AnsiUtils.map_position_to_coloured(
                display_line[coloured_word_start:], match_start_in_word
            )
            coloured_match_start_abs = coloured_word_start + coloured_match_start_in_word
            # Use plain text for matched part to avoid colour code conflicts
            plain_matched_part = match.text[match_start_in_word:match_end_in_word]
            coloured_match_end = AnsiUtils.map_position_to_coloured(
                display_line, word_start + match_end_in_word
            )

            # Wrap the matched substring with highlight colour (do not add label
            # here; we've already inserted/replaced it above)
            before_match = display_line[:coloured_match_start_abs]
            after_matched = display_line[coloured_match_end:]
            highlighted = f"{AnsiStyles.RESET}{self.config.highlight_colour}{plain_matched_part}{AnsiStyles.RESET}"
            display_line = before_match + highlighted + after_matched

        return display_line

    def _display_pane_content(self, lines: list, lines_plain: list, available_height: int):
        """
        Display the pane content with match highlighting.

        Args:
            lines: List of lines with ANSI codes
            lines_plain: List of plain lines without ANSI codes
            available_height: Maximum number of lines to display
        """
        content_lines_printed = 0
        total_lines = min(len(lines), available_height)

        for line_idx, (line, _line_plain) in enumerate(zip(lines, lines_plain)):
            # Stop if we've filled available height
            if content_lines_printed >= available_height:
                break

            matches_on_line = self.search_interface.get_matches_at_line(line_idx)
            is_last_line = content_lines_printed == total_lines - 1

            if not matches_on_line:
                # Dim the line if there are search results but none on this line
                output = self._dim_coloured_line(line) if self.search_query else line

                # Skip newline on last line to prevent blank line before search bar
                if is_last_line:
                    sys.stdout.write(output)
                    sys.stdout.flush()  # Flush immediately after last line
                else:
                    print(output)
                content_lines_printed += 1
                continue

            # For lines with matches, highlight the matched text and add labels
            dimmed_line = self._dim_coloured_line(line) if self.search_query else line
            # Pass the plain (ANSI-stripped) version of the line so we can inspect
            # plain characters (e.g. to detect a following space to overwrite).
            plain_line = lines_plain[line_idx]
            display_line = self._display_line_with_matches(dimmed_line, line_idx, plain_line)

            # Skip newline on last line to prevent blank line before search bar
            if is_last_line:
                sys.stdout.write(display_line)
                sys.stdout.flush()  # Flush immediately after last line
            else:
                print(display_line)
            content_lines_printed += 1

    def _display_content(self):
        """Display the pane content with visual distinction for matches."""
        self._clear_screen()

        # Create a version of the content with labels overlayed
        # Strip trailing newline to avoid empty line at end (tmux capture-pane adds one)
        lines = self.pane_content.rstrip("\n").split("\n")
        lines_plain = self.pane_content_plain.rstrip("\n").split("\n")

        # Get popup dimensions first
        try:
            popup_height = shutil.get_terminal_size().lines
        except OSError:
            popup_height = 40

        # Calculate available height for content
        # Reserve 1 line at bottom for search bar, and exclude the last captured line
        # (which is the user's shell prompt that we want to replace with our search bar)
        available_height = popup_height - 1

        # Remove the last line (user's prompt) so search bar replaces it
        if len(lines) > 0:
            lines = lines[:-1]
            lines_plain = lines_plain[:-1]

        # Trim lines array to exactly available_height
        # This ensures we display exactly the right number of lines
        if len(lines) > available_height:
            lines = lines[:available_height]
            lines_plain = lines_plain[:available_height]

        # If search bar is at the top, display it first
        if self.config.prompt_position == "top":
            search_output = self._build_search_bar_output()
            sys.stdout.write(search_output)
            sys.stdout.write("\n")

            # Set scrolling region to protect only the prompt (line 1)
            # Line 1 = prompt, Lines 2+ = scrollable content
            sys.stdout.write(f"\033[2;{popup_height}r")
            # Position cursor at start of scrollable region (line 2, column 1)
            sys.stdout.write("\033[2;1H")

            sys.stdout.flush()

        # If search bar is at the bottom, set up scrolling region first
        if self.config.prompt_position == "bottom":
            # Protect only bottom line (search bar)
            scrollable_bottom = popup_height - 1

            sys.stdout.write(f"\033[1;{scrollable_bottom}r")
            # Position cursor at start of scrollable region (line 1, column 1)
            sys.stdout.write("\033[1;1H")
            sys.stdout.flush()

        # Display pane content (limit to available height)
        self._display_pane_content(lines, lines_plain, available_height)

        # Position cursor at search input if search bar is at top
        if self.config.prompt_position == "top":
            # Move cursor to line 1 (search bar), column after prompt indicator
            cursor_col = len(self.config.prompt_indicator) + 2
            # Calculate position after the search query text
            if self.search_query:
                cursor_col += len(self.search_query)
            # ANSI escape: \033[{row};{col}H positions cursor at row, col (1-indexed)
            sys.stdout.write(f"\033[1;{cursor_col}H")
            sys.stdout.flush()

        # If search bar is at the bottom, render it in the protected area
        if self.config.prompt_position == "bottom":
            # Flush any pending output first
            sys.stdout.flush()

            search_output = self._build_search_bar_output()

            # Position search bar at last line
            search_bar_line = popup_height
            sys.stdout.write(f"\033[{search_bar_line};1H")
            # Write search bar
            sys.stdout.write(search_output)

            # Position cursor after the prompt and search query (on the left side)
            # Calculate the visible cursor position (ignore ANSI codes and right-aligned debug text)
            cursor_col = len(self.config.prompt_indicator) + 2
            if self.search_query:
                cursor_col += len(self.search_query)
            sys.stdout.write(f"\033[{cursor_col}G")

            sys.stdout.flush()

    def run(self) -> Optional[str]:
        """
        Run the interactive search UI.

        Returns:
            The selected text if a match was chosen, None if cancelled
        """
        try:
            self._display_content()

            while True:
                try:
                    char = self._get_single_char()
                except Exception as e:
                    # If we fail to read input, log and treat as cancel
                    if self.debug_logger and self.debug_logger.enabled:
                        self.debug_logger.log(f"Error reading character: {e}")
                    self._save_result("", should_paste=False)
                    return None

                # Ignore empty characters (escape sequences we want to skip)
                if char == "":
                    continue

                # Handle control characters
                if char == ControlChars.CTRL_C:
                    if self.debug_logger and self.debug_logger.enabled:
                        self.debug_logger.log("User cancelled with Ctrl+C")
                    self._save_result(
                        "", should_paste=False
                    )  # Write empty file to signal completion
                    return None
                elif char == ControlChars.ESC:
                    if self.debug_logger and self.debug_logger.enabled:
                        self.debug_logger.log("User cancelled with ESC")
                    self._save_result(
                        "", should_paste=False
                    )  # Write empty file to signal completion
                    return None
                elif char in (";", ":"):
                    # Semicolon/colon handling depends on auto-paste enabled setting
                    if self.config.auto_paste_enable:
                        # Auto-paste enabled: semicolon/colon acts as modifier
                        self.autopaste_modifier_active = True
                        # Only log if modifier state changed (avoid repetition when key is held)
                        if self.last_logged_modifier != char:
                            if self.debug_logger and self.debug_logger.enabled:
                                self.debug_logger.log(f"Auto-paste modifier activated ('{char}')")
                            self.last_logged_modifier = char
                        continue
                    else:
                        # Auto-paste disabled: treat semicolon/colon as regular searchable characters
                        self.last_logged_modifier = None  # Reset logged state
                        self._update_search(self.search_query + char)
                elif char == ControlChars.CTRL_U:  # Clear line
                    self.autopaste_modifier_active = False
                    self.last_logged_modifier = None
                    self._update_search("")
                elif char == ControlChars.CTRL_W:  # Delete word backwards
                    self.autopaste_modifier_active = False
                    self.last_logged_modifier = None
                    if self.search_query:
                        # Delete backwards treating delimiters as word boundaries
                        new_query = self.search_query.rstrip()  # Remove trailing whitespace
                        if new_query:
                            i = len(new_query) - 1
                            delimiters = " \t-_.,;:!?/\\()[]{}"
                            # If we're at a delimiter, skip backwards over delimiter(s) first
                            if new_query[i] in delimiters:
                                while i >= 0 and new_query[i] in delimiters:
                                    i -= 1
                            # Now skip backwards over the word (non-delimiter characters)
                            while i >= 0 and new_query[i] not in delimiters:
                                i -= 1
                            new_query = new_query[: i + 1]
                        self._update_search(new_query)
                elif char == ControlChars.BACKSPACE or char == ControlChars.BACKSPACE_ALT:
                    self.autopaste_modifier_active = False
                    self.last_logged_modifier = None
                    if self.search_query:
                        self._update_search(self.search_query[:-1])
                elif char == ControlChars.ENTER or char == ControlChars.ENTER_ALT:
                    if self.current_matches:
                        # Select the first match
                        # Use autopaste modifier if active
                        should_paste = self.autopaste_modifier_active
                        if self.debug_logger and self.debug_logger.enabled:
                            paste_msg = " with auto-paste" if should_paste else ""
                            self.debug_logger.log(
                                f"User pressed Enter{paste_msg} - selected first match: '{self.current_matches[0].text}'"
                            )
                        self._save_result(
                            self.current_matches[0].copy_text, should_paste=should_paste
                        )
                        return self.current_matches[0].copy_text
                elif char.isprintable():
                    # Check if this character is a label for current matches
                    # But only if we already have a non-empty search query
                    # (to avoid matching labels on the first character typed)
                    if self.current_matches and self.search_query:
                        match = self.search_interface.get_match_by_label(char)
                        if match:
                            # Label pressed - save result and exit
                            # Use autopaste modifier if active for auto-paste
                            should_paste = self.autopaste_modifier_active
                            if self.debug_logger and self.debug_logger.enabled:
                                paste_msg = " with auto-paste" if should_paste else ""
                                self.debug_logger.log(
                                    f"User selected label '{char}'{paste_msg}: '{match.text}'"
                                )
                            self._save_result(match.copy_text, should_paste=should_paste)
                            return match.copy_text

                    # Regular character - add to search query
                    # Don't reset modifier when typing (allows holding modifier while selecting)
                    self._update_search(self.search_query + char)

        except KeyboardInterrupt:
            self._save_result("", should_paste=False)  # Write empty file to signal completion
            return None
        finally:
            # Reset terminal state (scrolling region)
            self._reset_terminal()
            # Clean up terminal
            self._clear_screen()

    def _save_result(self, text: str, should_paste: bool = False):
        """Save the result to a file for the parent process.

        Args:
            text: The selected text to copy
            should_paste: Whether to auto-paste after copying
        """
        result_file = os.path.join(self.temp_dir, "result.txt")
        with open(result_file, "w") as f:
            f.write(text)

        # Save paste flag to separate file
        paste_flag_file = os.path.join(self.temp_dir, "should_paste.txt")
        with open(paste_flag_file, "w") as f:
            f.write("true" if should_paste else "false")


def main():
    """Main entry point for the interactive UI."""
    parser = argparse.ArgumentParser(description="Interactive search UI for tmux-flash-copy")
    parser.add_argument("--pane-id", required=True, help="The tmux pane ID")
    parser.add_argument("--temp-dir", required=True, help="Temporary directory path")
    parser.add_argument(
        "--pane-content-file", default="", help="Path to file containing pane content"
    )
    parser.add_argument(
        "--reverse-search", default="True", help="Enable reverse search (bottom to top)"
    )
    parser.add_argument("--word-separators", default="", help="Word separator characters")
    parser.add_argument("--case-sensitive", default="False", help="Enable case-sensitive search")
    parser.add_argument(
        "--prompt-placeholder-text", default="search...", help="Ghost text for empty prompt input"
    )
    parser.add_argument(
        "--highlight-colour", default="\033[1;33m", help="ANSI colour for highlighted text"
    )
    parser.add_argument("--label-colour", default="\033[1;32m", help="ANSI colour for labels")
    parser.add_argument(
        "--prompt-position", default="bottom", help="Position of prompt (top or bottom)"
    )
    parser.add_argument("--prompt-indicator", default=">", help="Prompt character/string")
    parser.add_argument("--prompt-colour", default="\033[1m", help="ANSI colour for the prompt")
    parser.add_argument("--debug-enabled", default="false", help="Enable debug logging")
    parser.add_argument("--debug-log-file", default="", help="Path to debug log file")
    parser.add_argument(
        "--auto-paste", default="true", help="Enable auto-paste modifier functionality"
    )
    parser.add_argument(
        "--label-characters",
        default="",
        help="Custom label characters to use for match labels (overrides default)",
    )

    args = parser.parse_args()

    try:
        # Get pane content - either from file (fast) or by capturing (fallback)
        if args.pane_content_file and os.path.exists(args.pane_content_file):
            # Read from file to avoid redundant capture
            try:
                with open(args.pane_content_file) as f:
                    pane_content = f.read()
            except OSError:
                # File read failed, fall back to capturing
                capture = PaneCapture(args.pane_id)
                pane_content = capture.capture_pane()
        else:
            # No file provided or doesn't exist, capture directly
            capture = PaneCapture(args.pane_id)
            pane_content = capture.capture_pane()

        # Get pane dimensions
        capture = PaneCapture(args.pane_id)
        dimensions = capture.get_pane_dimensions()

        # Reconstruct FlashCopyConfig from command line arguments
        config = FlashCopyConfig(
            reverse_search=args.reverse_search.lower() in ("true", "1", "yes", "on"),
            case_sensitive=args.case_sensitive.lower() in ("true", "1", "yes", "on"),
            word_separators=args.word_separators if args.word_separators else None,
            prompt_placeholder_text=args.prompt_placeholder_text,
            highlight_colour=args.highlight_colour,
            label_colour=args.label_colour,
            prompt_position=args.prompt_position,
            prompt_indicator=args.prompt_indicator,
            prompt_colour=args.prompt_colour,
            debug_enabled=args.debug_enabled.lower() in ("true", "1", "yes", "on"),
            auto_paste_enable=args.auto_paste.lower() in ("true", "1", "yes", "on"),
            label_characters=args.label_characters if args.label_characters else None,
        )

        # Initialize debug logger if enabled
        if config.debug_enabled and args.debug_log_file:
            logger = DebugLogger.get_instance(enabled=True, log_file=args.debug_log_file)
            logger.log_section("Interactive UI Session")
            logger.log(f"Pane dimensions: {dimensions}")

        # Run interactive UI
        ui = InteractiveUI(args.pane_id, args.temp_dir, pane_content, dimensions, config)
        ui.run()

        # Exit explicitly to close the popup
        sys.exit(0)

    except Exception as e:
        import traceback

        error_msg = f"Error: {e}\n{traceback.format_exc()}"
        print(error_msg, file=sys.stderr)


if __name__ == "__main__":
    main()
