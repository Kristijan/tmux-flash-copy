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
        )
        self.clipboard = Clipboard()
        self.search_query = ""
        self.current_matches = []
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
        Read a single character from stdin without waiting for Enter.

        Returns:
            The character read, or empty string on EOF
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
                return char

            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                char = sys.stdin.read(1)
                if not char:  # EOF
                    return ControlChars.CTRL_C  # Treat EOF as Ctrl+C
                return char
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        except Exception as e:
            print(f"Error reading input: {e}", file=sys.stderr)
            return ControlChars.CTRL_C  # Treat any error as Ctrl+C

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

    def _get_separator_line(self, term_width: int) -> str:
        """
        Build the separator line.

        Args:
            term_width: Terminal width in characters

        Returns:
            The formatted separator line
        """
        separator = "─" * term_width
        return f"{self.config.prompt_separator_colour}{separator}{AnsiStyles.RESET}"

    def _display_line_with_matches(self, display_line: str, line_idx: int) -> str:
        """
        Process and format a line that contains matches.

        Applies highlighting to matched text and adds match labels.

        Args:
            display_line: The line content with ANSI codes
            line_idx: The line index in the pane content

        Returns:
            The line with highlights and labels applied
        """
        matches_on_line = self.search_interface.get_matches_at_line(line_idx)

        # Process matches from right to left to maintain position accuracy
        for match in sorted(matches_on_line, key=lambda m: m.col, reverse=True):
            if not match.label:
                continue

            # Get the matched word and its position
            word_start = match.col
            word_end = match.col + len(match.text)
            match_start_in_word = match.match_start
            match_end_in_word = match.match_end

            # Find positions in coloured line using AnsiUtils
            coloured_word_start = AnsiUtils.map_position_to_coloured(display_line, word_start)
            coloured_word_end = AnsiUtils.map_position_to_coloured(display_line, word_end)
            coloured_match_start_in_word = AnsiUtils.map_position_to_coloured(
                display_line[coloured_word_start:], match_start_in_word
            )

            # Build the replacement for this word with highlighting
            # Split into: before match, matched part (yellow), after match, label (green)
            before_match = display_line[
                coloured_word_start : coloured_word_start + coloured_match_start_in_word
            ]

            # Find the end position of the matched part in coloured line
            plain_match_end = word_start + match_end_in_word
            coloured_match_end = AnsiUtils.map_position_to_coloured(display_line, plain_match_end)

            # Use plain text for matched part to avoid colour code conflicts
            plain_matched_part = match.text[match_start_in_word:match_end_in_word]
            after_word = display_line[coloured_word_end:]

            # Build replacement with highlight and label colours
            replacement = f"{before_match}{AnsiStyles.RESET}{self.config.highlight_colour}{plain_matched_part}{AnsiStyles.RESET}{self.config.label_colour}{match.label}{AnsiStyles.RESET}{AnsiStyles.DIM}{display_line[coloured_match_end:coloured_word_end]}"

            # Replace in display line
            display_line = display_line[:coloured_word_start] + replacement + after_word

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
        for line_idx, (line, _line_plain) in enumerate(zip(lines, lines_plain)):
            # Stop if we've filled available height
            if content_lines_printed >= available_height:
                break

            matches_on_line = self.search_interface.get_matches_at_line(line_idx)

            if not matches_on_line:
                # Dim the line if there are search results but none on this line
                if self.search_query:
                    # Apply dimming that works with coloured content
                    print(self._dim_coloured_line(line))
                else:
                    print(line)
                content_lines_printed += 1
                continue

            # For lines with matches, highlight the matched text and add labels
            dimmed_line = self._dim_coloured_line(line) if self.search_query else line
            display_line = self._display_line_with_matches(dimmed_line, line_idx)
            print(display_line)
            content_lines_printed += 1

    def _display_content(self):
        """Display the pane content with visual distinction for matches."""
        self._clear_screen()

        # Create a version of the content with labels overlayed
        lines = self.pane_content.split("\n")
        lines_plain = self.pane_content_plain.split("\n")

        try:
            popup_height = shutil.get_terminal_size().lines
            term_width = shutil.get_terminal_size().columns
        except OSError:
            popup_height = 40
            term_width = 80

        # Calculate available height for content
        # Account for separator line and search bar (2 lines) plus margins
        available_height = popup_height - 3  # -1 for search, -1 for separator, -1 for safety

        # If search bar is at the top, display it first
        if self.config.prompt_position == "top":
            search_output = self._build_search_bar_output()
            sys.stdout.write(search_output)
            sys.stdout.write("\n")

            # Display separator line
            print(self._get_separator_line(term_width))

            # Set scrolling region to protect the prompt (lines 1-2) from scrolling
            # ANSI escape: \033[{top};{bottom}r sets scrolling region
            # Line 1 = prompt, Line 2 = separator, Lines 3+ = scrollable content
            sys.stdout.write(f"\033[3;{popup_height}r")

            # Position cursor at start of scrollable region (line 3, column 1)
            sys.stdout.write("\033[3;1H")
            sys.stdout.flush()

        # If search bar is at the bottom, set up scrolling region first
        if self.config.prompt_position == "bottom":
            # Set scrolling region to protect the bottom 2 lines (separator + search bar)
            # ANSI escape: \033[{top};{bottom}r sets scrolling region
            # Lines 1 to (height - 2) are scrollable, last 2 lines are protected
            scrollable_bottom = popup_height - 2
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

            # Build the complete bottom output
            separator = self._get_separator_line(term_width)
            search_output = self._build_search_bar_output()

            # Position cursor at the separator line (second-to-last line)
            separator_line = popup_height - 1
            sys.stdout.write(f"\033[{separator_line};1H")

            # Write separator and search bar
            sys.stdout.write(f"{separator}\n{search_output}")

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
                char = self._get_single_char()

                # Handle control characters
                if char == ControlChars.CTRL_C:
                    if self.debug_logger and self.debug_logger.enabled:
                        self.debug_logger.log("User cancelled with Ctrl+C")
                    self._save_result("")  # Write empty file to signal completion
                    return None
                elif char == ControlChars.ESC:
                    if self.debug_logger and self.debug_logger.enabled:
                        self.debug_logger.log("User cancelled with ESC")
                    self._save_result("")  # Write empty file to signal completion
                    return None
                elif char == ControlChars.CTRL_U:  # Clear line
                    self._update_search("")
                elif char == ControlChars.CTRL_W:  # Delete word backwards
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
                    if self.search_query:
                        self._update_search(self.search_query[:-1])
                elif char == ControlChars.ENTER or char == ControlChars.ENTER_ALT:
                    if self.current_matches:
                        # Select the first match
                        if self.debug_logger and self.debug_logger.enabled:
                            self.debug_logger.log(
                                f"User pressed Enter - selected first match: '{self.current_matches[0].text}'"
                            )
                        self._save_result(self.current_matches[0].text)
                        return self.current_matches[0].text
                elif char.isprintable():
                    # Check if this character is a label for current matches
                    # But only if we already have a non-empty search query
                    # (to avoid matching labels on the first character typed)
                    if self.current_matches and self.search_query:
                        match = self.search_interface.get_match_by_label(char)
                        if match:
                            # Label pressed - save result and exit
                            # Parent process handles clipboard/paste
                            if self.debug_logger and self.debug_logger.enabled:
                                self.debug_logger.log(
                                    f"User selected label '{char}': '{match.text}'"
                                )
                            self._save_result(match.text)
                            return match.text

                    # Regular character - add to search query
                    self._update_search(self.search_query + char)

        except KeyboardInterrupt:
            self._save_result("")  # Write empty file to signal completion
            return None
        finally:
            # Reset terminal state (scrolling region)
            self._reset_terminal()
            # Clean up terminal
            self._clear_screen()

    def _save_result(self, text: str):
        """Save the result to a file for the parent process."""
        result_file = os.path.join(self.temp_dir, "result.txt")
        with open(result_file, "w") as f:
            f.write(text)


def main():
    """Main entry point for the interactive UI."""
    parser = argparse.ArgumentParser(description="Interactive search UI for tmux-flash-copy")
    parser.add_argument("--pane-id", required=True, help="The tmux pane ID")
    parser.add_argument("--temp-dir", required=True, help="Temporary directory path")
    parser.add_argument(
        "--pane-content-file", default="", help="Path to file containing pane content"
    )
    parser.add_argument("--ui-mode", default="popup", help="UI mode: popup, window")
    parser.add_argument(
        "--reverse-search", default="True", help="Enable reverse search (bottom to top)"
    )
    parser.add_argument("--word-separators", default="", help="Word separator characters")
    parser.add_argument("--case-sensitive", default="False", help="Enable case-sensitive search")
    parser.add_argument("--auto-paste", default="False", help="Automatically paste after copying")
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
    parser.add_argument(
        "--prompt-separator-colour",
        default="\033[38;5;242m",
        help="ANSI colour for the prompt separator line",
    )
    parser.add_argument("--debug-enabled", default="false", help="Enable debug logging")
    parser.add_argument("--debug-log-file", default="", help="Path to debug log file")

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
            ui_mode=args.ui_mode,
            auto_paste=args.auto_paste.lower() in ("true", "1", "yes", "on"),
            reverse_search=args.reverse_search.lower() in ("true", "1", "yes", "on"),
            case_sensitive=args.case_sensitive.lower() in ("true", "1", "yes", "on"),
            word_separators=args.word_separators if args.word_separators else None,
            prompt_placeholder_text=args.prompt_placeholder_text,
            highlight_colour=args.highlight_colour,
            label_colour=args.label_colour,
            prompt_position=args.prompt_position,
            prompt_indicator=args.prompt_indicator,
            prompt_colour=args.prompt_colour,
            prompt_separator_colour=args.prompt_separator_colour,
            debug_enabled=args.debug_enabled.lower() in ("true", "1", "yes", "on"),
        )

        # Initialize debug logger if enabled
        if config.debug_enabled and args.debug_log_file:
            logger = DebugLogger.get_instance(enabled=True, log_file=args.debug_log_file)
            logger.log_section("Interactive UI Session")
            logger.log(f"UI mode: {config.ui_mode}")
            logger.log(f"Pane dimensions: {dimensions}")

        # Run interactive UI
        ui = InteractiveUI(args.pane_id, args.temp_dir, pane_content, dimensions, config)
        result = ui.run()

        # In window mode, we must handle clipboard/paste ourselves (parent has exited)
        # In popup mode, the parent process handles it
        if result and config.ui_mode == "window":
            logger = DebugLogger.get_instance() if config.debug_enabled else None
            ui.clipboard.copy_and_paste(
                result, pane_id=args.pane_id, auto_paste=config.auto_paste, logger=logger
            )

        # Clean up temp directory in window mode (parent has already exited)
        if config.ui_mode == "window":
            try:
                import shutil

                shutil.rmtree(args.temp_dir, ignore_errors=True)
            except Exception:
                pass  # Ignore cleanup errors

        # Exit explicitly to close the popup/window
        sys.exit(0)

    except Exception as e:
        import traceback

        error_msg = f"Error: {e}\n{traceback.format_exc()}"
        print(error_msg, file=sys.stderr)


if __name__ == "__main__":
    main()
