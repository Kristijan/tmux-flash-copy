"""
Popup UI module for the interactive search interface.

This module creates a tmux popup window that displays the pane content
with a search interface, labels for matches, and handles user input.
"""

import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional

from src.clipboard import Clipboard
from src.config import FlashCopyConfig
from src.debug_logger import DebugLogger
from src.search_interface import SearchInterface, SearchMatch
from src.utils import FileUtils, TmuxPaneUtils


class PopupUI:
    """Manages the interactive popup UI for searching and selecting."""

    def __init__(
        self,
        pane_content: str,
        search_interface: SearchInterface,
        clipboard: Clipboard,
        pane_id: str,
        config: FlashCopyConfig,
    ):
        """
        Initialise the popup UI.

        Args:
            pane_content: The captured pane content
            search_interface: SearchInterface instance for searching
            clipboard: Clipboard instance for copying
            pane_id: The tmux pane ID
            config: FlashCopyConfig with all configuration options
        """
        self.pane_content = pane_content
        self.search_interface = search_interface
        self.clipboard = clipboard
        self.pane_id = pane_id
        self.config = config
        self.temp_dir = tempfile.mkdtemp()
        self.search_query = ""
        self.current_matches: list[SearchMatch] = []

    def run(self) -> tuple[Optional[str], bool]:
        """
        Run the interactive popup UI.

        Returns:
            Tuple of (text, should_paste) where text is the copied text if selection
            was made (None if cancelled) and should_paste is True if auto-paste is enabled
        """
        try:
            # Launch the popup
            result = self._launch_popup()

            return result

        finally:
            # Cleanup
            self._cleanup()

    def _launch_popup(self) -> tuple[Optional[str], bool]:
        """
        Launch the tmux popup window.

        Returns:
            Tuple of (text, should_paste) where text is the copied text if selection
            was made (None if cancelled) and should_paste is True if auto-paste is enabled
        """
        # Save pane content to temp file to avoid re-capturing in interactive script
        pane_content_file = os.path.join(self.temp_dir, "pane_content.txt")
        try:
            with open(pane_content_file, "w") as f:
                f.write(self.pane_content)
        except OSError:
            # If we can't write the file, the interactive script will fall back to capturing
            pass

        # Get pane dimensions for seamless overlay positioning
        pane_dimensions = TmuxPaneUtils.get_pane_dimensions(self.pane_id)

        if pane_dimensions:
            # Calculate popup position to perfectly overlay the pane
            popup_pos = TmuxPaneUtils.calculate_popup_position(pane_dimensions)
            popup_x = popup_pos["x"]
            popup_y = popup_pos["y"]
            popup_width = popup_pos["width"]
            popup_height = popup_pos["height"]
        else:
            # Fallback: Get window dimensions if pane dimensions unavailable
            try:
                result = subprocess.run(
                    ["tmux", "display-message", "-p", "#{window_width},#{window_height}"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                popup_width, popup_height = map(int, result.stdout.strip().split(","))
                popup_x = 0
                popup_y = 0
            except (subprocess.SubprocessError, ValueError):
                popup_width = 160
                popup_height = 40
                popup_x = 0
                popup_y = 0

        # Create a command that will be executed in the popup
        # We'll use a custom Python script for better control
        plugin_dir = Path(__file__).parent.parent
        interactive_script = plugin_dir / "bin" / "tmux-flash-copy-interactive.py"

        # Launch tmux popup with the interactive UI
        # -E: close popup on exit
        # -B: no border for seamless look
        # Position and size to seamlessly overlay the calling pane
        popup_cmd = [
            "tmux",
            "display-popup",
            "-E",
            "-B",
            "-x",
            str(popup_x),
            "-y",
            str(popup_y),
            "-w",
            str(popup_width),
            "-h",
            str(popup_height),
            str(interactive_script),
            "--pane-id",
            self.pane_id,
            "--temp-dir",
            self.temp_dir,
            "--pane-content-file",
            pane_content_file,
            "--reverse-search",
            str(self.search_interface.reverse_search),
            "--word-separators",
            self.search_interface.word_separators or "",
            "--case-sensitive",
            str(self.config.case_sensitive),
            "--prompt-placeholder-text",
            self.config.prompt_placeholder_text,
            "--highlight-colour",
            self.config.highlight_colour,
            "--label-colour",
            self.config.label_colour,
            "--prompt-position",
            self.config.prompt_position,
            "--prompt-indicator",
            self.config.prompt_indicator,
            "--prompt-colour",
            self.config.prompt_colour,
            "--debug-enabled",
            "true" if self.config.debug_enabled else "false",
            "--debug-log-file",
            DebugLogger.get_instance().log_file if self.config.debug_enabled else "",
            "--label-characters",
            self.config.label_characters or "",
            "--auto-paste",
            "true" if self.config.auto_paste_enable else "false",
        ]

        try:
            # Run the popup command - it will close automatically with -E flag when script exits
            subprocess.run(
                popup_cmd,
                check=False,
            )

            # Read the result from the temp directory with retries
            result_file = os.path.join(self.temp_dir, "result.txt")
            result_text = self._wait_for_result_file(result_file, timeout=5.0)

            # Read the paste flag
            paste_flag_file = os.path.join(self.temp_dir, "should_paste.txt")
            should_paste = self._read_paste_flag(paste_flag_file)

            # Empty string means cancelled (ESC/Ctrl+C)
            # None means file was never created (timeout)
            if result_text is not None and result_text != "":
                # Return tuple of (text, should_paste)
                return (result_text, should_paste)

            # Return tuple of (None, False) for cancelled or timeout
            return (None, False)

        except Exception:
            return (None, False)

    def _cleanup(self):
        """Clean up temporary files."""
        FileUtils.cleanup_dir(self.temp_dir)

    def _wait_for_result_file(self, result_file: str, timeout: float = 5.0) -> Optional[str]:
        """
        Wait for the result file to be written by the interactive UI.

        Args:
            result_file: Path to the result file
            timeout: Maximum time to wait in seconds (default 5.0)

        Returns:
            The result text if file is found and readable, None otherwise
        """
        start_time = time.time()
        poll_interval = 0.05  # Poll every 50ms

        while time.time() - start_time < timeout:
            if os.path.exists(result_file):
                try:
                    with open(result_file) as f:
                        result_text = f.read().strip()
                        return result_text
                except OSError:
                    # File may still be being written, try again
                    time.sleep(poll_interval)
                    continue
            else:
                # File doesn't exist yet, wait a bit and try again
                time.sleep(poll_interval)

        # Timeout reached, file was never found or readable
        return None

    def _read_paste_flag(self, paste_flag_file: str) -> bool:
        """
        Read the paste flag from the file written by interactive UI.

        Args:
            paste_flag_file: Path to the paste flag file

        Returns:
            True if paste flag is "true", False otherwise
        """
        if os.path.exists(paste_flag_file):
            try:
                with open(paste_flag_file) as f:
                    content = f.read().strip().lower()
                    return content == "true"
            except OSError:
                return False
        return False
