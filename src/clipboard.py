"""Clipboard module for tmux environments.

Uses tmux's built-in OSC52 support (tmux 3.2+) to copy to system clipboard,
with native system tools (pbcopy/xclip) as fallbacks when available.
"""

import os
import sys
from typing import Optional

from src.utils import SubprocessUtils


class Clipboard:
    """Handles copying text to the clipboard when running inside tmux.

    Returns True on success, False on failure.
    """

    @staticmethod
    def _tmux_osc52(text: str) -> bool:
        """Use tmux set-buffer -w to copy via OSC52.

        The -w flag tells tmux to send the buffer to the system clipboard
        via OSC52 passthrough (requires tmux 3.2+ and terminal OSC52 support).
        """
        return SubprocessUtils.run_command_quiet(["tmux", "set-buffer", "-w", "--", text])

    @staticmethod
    def _pbcopy(text: str) -> bool:
        """Use pbcopy (macOS native clipboard)."""
        return SubprocessUtils.run_command_with_input(["pbcopy"], text)

    @staticmethod
    def _xclip(text: str) -> bool:
        """Use xclip (Linux X11 clipboard)."""
        return SubprocessUtils.run_command_with_input(["xclip", "-selection", "clipboard"], text)

    @staticmethod
    def _xsel(text: str) -> bool:
        """Use xsel (Linux X11 clipboard fallback)."""
        return SubprocessUtils.run_command_with_input(["xsel", "--clipboard", "--input"], text)

    @staticmethod
    def _tmux_buffer(text: str) -> bool:
        """Store text in tmux buffer (allows pasting within tmux only)."""
        return SubprocessUtils.run_command_quiet(["tmux", "set-buffer", "--", text])

    @staticmethod
    def copy(text: str, logger=None) -> bool:
        """Copy text to clipboard using available methods.

        Args:
            text: Text to copy
            logger: Optional DebugLogger instance for logging

        Returns True on success, False on failure.
        """
        # Plugin runs inside tmux; require TMUX env var
        if "TMUX" not in os.environ:
            if logger:
                logger.log("Clipboard: Failed - not in tmux")
            return False

        # Try tmux OSC52 passthrough first (tmux 3.2+)
        if Clipboard._tmux_osc52(text):
            if logger:
                logger.log("Clipboard: Success via tmux OSC52")
            return True

        # Try native system clipboard tools as fallback
        if sys.platform == "darwin":
            if Clipboard._pbcopy(text):
                if logger:
                    logger.log("Clipboard: Success via pbcopy (macOS)")
                return True
        elif sys.platform == "linux":
            if Clipboard._xclip(text):
                if logger:
                    logger.log("Clipboard: Success via xclip (Linux)")
                return True
            if Clipboard._xsel(text):
                if logger:
                    logger.log("Clipboard: Success via xsel (Linux)")
                return True

        # Last resort: tmux buffer (pasting within tmux only)
        if Clipboard._tmux_buffer(text):
            if logger:
                logger.log("Clipboard: Success via tmux buffer (tmux-only)")
            return True

        if logger:
            logger.log("Clipboard: All methods failed")
        return False

    @staticmethod
    def copy_and_paste(
        text: str, pane_id: Optional[str] = None, auto_paste: bool = False, logger=None
    ) -> bool:
        """Copy text to clipboard and optionally paste to pane.

        Args:
            text: Text to copy
            pane_id: Target pane ID for paste (required if auto_paste=True)
            auto_paste: If True, paste text to pane after copying
            logger: Optional DebugLogger instance for logging

        Returns:
            True if copy succeeded (paste failures are silent)
        """
        # Copy to clipboard first
        if not Clipboard.copy(text, logger=logger):
            return False

        # Optionally paste to pane
        if auto_paste and pane_id:
            try:
                SubprocessUtils.run_command_quiet(["tmux", "set-buffer", "-b", "flash-paste", text])
                SubprocessUtils.run_command_quiet(
                    ["tmux", "paste-buffer", "-b", "flash-paste", "-t", pane_id]
                )
                if logger:
                    logger.log(f"Auto-paste to pane {pane_id}: Success")
            except Exception:
                if logger:
                    logger.log(f"Auto-paste to pane {pane_id}: Failed")
                pass  # Silent fail on paste errors

        return True
