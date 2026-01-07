"""
Popup UI module for the interactive search interface.

This module creates a tmux popup window that displays the pane content
with a search interface, labels for matches, and handles user input.
"""

import subprocess
from pathlib import Path
from typing import Optional

from src.clipboard import Clipboard
from src.config import FlashCopyConfig
from src.debug_logger import DebugLogger
from src.search_interface import SearchInterface, SearchMatch
from src.utils import TmuxPaneUtils


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
        self.search_query = ""
        self.current_matches: list[SearchMatch] = []

    def run(self) -> tuple[Optional[str], bool]:
        """
        Run the interactive popup UI.

        Returns:
            Tuple of (text, should_paste) where text is the copied text if selection
            was made (None if cancelled) and should_paste is True if auto-paste is enabled
        """
        # Launch the popup
        result = self._launch_popup()

        return result

    def _launch_popup(self) -> tuple[Optional[str], bool]:
        """
        Launch the tmux popup window.

        Returns:
            Tuple of (text, should_paste) where text is the copied text if selection
            was made (None if cancelled) and should_paste is True if auto-paste is enabled
        """
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

        logger = DebugLogger.get_instance()

        try:
            # Run the popup command - it will close automatically with -E flag when script exits
            # Long timeout (5 minutes) to allow users time to search and select text
            result = subprocess.run(
                popup_cmd,
                check=False,
                timeout=300.0,
            )

            if logger.enabled:
                logger.log(f"Popup closed with exit code: {result.returncode}")

            # Read paste flag from exit code: 10 = paste, 0 = copy
            should_paste = result.returncode == 10

            # Read result from tmux buffer (written by child process)
            # Using unique buffer name to avoid conflicts
            try:
                if logger.enabled:
                    logger.log("Reading result from tmux buffer...")

                buffer_result = subprocess.run(
                    ["tmux", "show-buffer", "-b", "__tmux_flash_copy_result__"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                result_text = buffer_result.stdout.strip() if buffer_result.stdout else None

                if logger.enabled:
                    if result_text:
                        logger.log(f"Buffer read successful (length: {len(result_text)})")
                    else:
                        logger.log("Buffer read returned empty string")

                # Clean up the buffer after reading
                subprocess.run(
                    ["tmux", "delete-buffer", "-b", "__tmux_flash_copy_result__"],
                    capture_output=True,
                    check=False,
                )
            except subprocess.CalledProcessError as e:
                # Buffer doesn't exist (user cancelled or error)
                if logger.enabled:
                    logger.log(f"Buffer read FAILED: {e}")
                result_text = None

            # Empty string means cancelled (ESC/Ctrl+C)
            # None means no output or buffer not found
            if result_text is not None and result_text != "":
                if logger.enabled:
                    logger.log(f"Returning result to parent: '{result_text[:50]}...' (paste={should_paste})")
                # Return tuple of (text, should_paste)
                return (result_text, should_paste)

            # Return tuple of (None, False) for cancelled or no output
            if logger.enabled:
                logger.log("No result to return (cancelled or empty)")
            return (None, False)

        except subprocess.TimeoutExpired:
            if logger.enabled:
                logger.log("Popup timeout expired")
            return (None, False)
        except Exception as e:
            if logger.enabled:
                logger.log(f"Exception in _launch_popup: {e}")
            return (None, False)
