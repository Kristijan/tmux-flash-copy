"""
Pane capture module for extracting visible content and dimensions from tmux panes.
"""

import subprocess


class PaneCapture:
    """Captures content and dimensions from a tmux pane."""

    def __init__(self, pane_id: str):
        """
        Initialise the pane capture.

        Args:
            pane_id: The tmux pane ID (e.g., "%0")
        """
        self.pane_id = pane_id

    def capture_pane(self) -> str:
        """
        Capture the visible content of the pane, including colour codes.

        Returns:
            The visible text content of the pane with ANSI colour/style codes preserved
        """
        try:
            result = subprocess.run(
                ["tmux", "capture-pane", "-p", "-e", "-J", "-t", self.pane_id],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to capture pane {self.pane_id}: {e}") from e

    def get_pane_dimensions(self) -> dict[str, int]:
        """
        Get the width and height of the pane.

        Returns:
            Dictionary with 'width' and 'height' keys
        """
        try:
            result = subprocess.run(
                [
                    "tmux",
                    "display-message",
                    "-t",
                    self.pane_id,
                    "-p",
                    "#{pane_width},#{pane_height}",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            width, height = map(int, result.stdout.strip().split(","))
            return {"width": width, "height": height}
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get pane dimensions: {e}") from e
