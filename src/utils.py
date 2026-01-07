"""
Subprocess utilities module for consistent command execution.

Provides helper functions for running shell commands with uniform error handling,
timeouts, and logging.
"""

import subprocess
from dataclasses import dataclass
from typing import Optional


class SubprocessUtils:
    """Utilities for running subprocess commands with consistent error handling."""

    DEFAULT_TIMEOUT = 5  # seconds

    @staticmethod
    def run_command(
        cmd: list[str],
        default: str = "",
        capture_output: bool = True,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> str:
        """
        Run a command and return its output.

        Provides consistent error handling with sensible defaults. Errors and
        timeouts return the default value instead of raising exceptions.

        Args:
            cmd: Command and arguments as a list
            default: Default value to return on error or if command fails
            capture_output: If True, capture stdout; if False, run silently
            timeout: Timeout in seconds (default 5)

        Returns:
            The stdout output if successful, otherwise the default value
        """
        try:
            result = subprocess.run(
                cmd, capture_output=capture_output, text=True, check=False, timeout=timeout
            )
            if result.returncode == 0:
                return result.stdout.strip() if capture_output else ""
            return default
        except (subprocess.SubprocessError, OSError, TimeoutError):
            return default

    @staticmethod
    def run_command_quiet(cmd: list[str], timeout: int = DEFAULT_TIMEOUT) -> bool:
        """
        Run a command silently and return success/failure status.

        Args:
            cmd: Command and arguments as a list
            timeout: Timeout in seconds (default 5)

        Returns:
            True if command succeeded (returncode 0), False otherwise
        """
        try:
            result = subprocess.run(cmd, capture_output=True, check=False, timeout=timeout)
            return result.returncode == 0
        except (subprocess.SubprocessError, OSError, TimeoutError):
            return False

    @staticmethod
    def run_command_with_input(
        cmd: list[str], input_text: str, timeout: int = DEFAULT_TIMEOUT
    ) -> bool:
        """
        Run a command with text input and return success status.

        Useful for commands like pbcopy/xclip that read from stdin.

        Args:
            cmd: Command and arguments as a list
            input_text: Text to send to stdin
            timeout: Timeout in seconds (default 5)

        Returns:
            True if command succeeded, False otherwise
        """
        try:
            result = subprocess.run(
                cmd,
                input=input_text.encode("utf-8"),
                capture_output=True,
                check=False,
                timeout=timeout,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, OSError, TimeoutError):
            return False


@dataclass
class PaneDimensions:
    """Represents the dimensions and position of a tmux pane."""

    pane_id: str
    left: int
    top: int
    right: int
    bottom: int
    width: int
    height: int


class TmuxPaneUtils:
    """Utilities for tmux pane operations and popup positioning."""

    @staticmethod
    def get_pane_dimensions(pane_id: str) -> Optional[PaneDimensions]:
        """
        Get the dimensions and position of a specific tmux pane.

        Args:
            pane_id: The tmux pane ID (e.g., '%0', '%1')

        Returns:
            PaneDimensions object with pane info, or None if retrieval fails
        """
        try:
            # Use display-message to get info for the specific pane
            result = subprocess.run(
                [
                    "tmux",
                    "display-message",
                    "-t",
                    pane_id,
                    "-p",
                    "#{pane_id} #{pane_left} #{pane_top} #{pane_right} #{pane_bottom} #{pane_width} #{pane_height}",
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=2,
            )

            # Parse the output
            parts = result.stdout.strip().split()
            if len(parts) != 7:
                return None

            return PaneDimensions(
                pane_id=parts[0],
                left=int(parts[1]),
                top=int(parts[2]),
                right=int(parts[3]),
                bottom=int(parts[4]),
                width=int(parts[5]),
                height=int(parts[6]),
            )
        except (subprocess.SubprocessError, ValueError, IndexError, OSError):
            return None

    @staticmethod
    def calculate_popup_position(dimensions: PaneDimensions) -> dict:
        """
        Calculate the popup positioning parameters to seamlessly overlay a pane.

        Based on tmux popup coordinate behavior:
        - For panes at the top (top=0): y = pane_top
        - For other panes: y = pane_bottom + 1 (to account for the border above the pane)
        - x always = pane_left
        - width and height match the pane dimensions

        Args:
            dimensions: PaneDimensions object with pane info

        Returns:
            Dictionary with keys 'x', 'y', 'width', 'height' for popup positioning
        """
        # Determine y position based on whether pane is at the top
        # For non-top panes, add 1 to account for the border above the pane
        y_position = dimensions.top if dimensions.top == 0 else dimensions.bottom + 1

        return {
            "x": dimensions.left,
            "y": y_position,
            "width": dimensions.width,
            "height": dimensions.height,
        }
