"""
Debug logging module for tmux-flash-copy.

Provides centralized debug logging with automatic rotation and thread-safe writes.
Only logs when @flash-copy-debug is enabled.
"""

import os
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional


class DebugLogger:
    """Thread-safe debug logger with automatic rotation."""

    _instance: Optional["DebugLogger"] = None
    _lock = threading.Lock()

    MAX_LOG_SIZE = 5 * 1024 * 1024  # 5MB
    BACKUP_COUNT = 2  # Keep .log, .log.1, .log.2

    def __init__(self, enabled: bool = False, log_file: Optional[str] = None):
        """Initialize the debug logger.

        Args:
            enabled: Whether debug logging is enabled
            log_file: Path to log file (default: ~/.tmux-flash-copy-debug.log)
        """
        self.enabled = enabled
        self.log_file = log_file or self._get_default_log_path()
        self._file_handle = None

        if self.enabled:
            self._ensure_log_file()

    @classmethod
    def get_instance(cls, enabled: bool = False, log_file: Optional[str] = None) -> "DebugLogger":
        """Get or create the singleton logger instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(enabled, log_file)
        # Type checker: _instance is guaranteed to be DebugLogger here
        assert cls._instance is not None
        return cls._instance

    @staticmethod
    def _get_default_log_path() -> str:
        """Get the default log file path."""
        # Try home directory first
        try:
            home = Path.home()
            log_path = home / ".tmux-flash-copy-debug.log"
            # Test write access
            log_path.touch(exist_ok=True)
            return str(log_path)
        except (OSError, PermissionError):
            # Fallback to /tmp with UID to avoid conflicts
            uid = os.getuid()
            return f"/tmp/tmux-flash-copy-debug-{uid}.log"

    def _ensure_log_file(self):
        """Ensure log file exists and is writable."""
        try:
            log_path = Path(self.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            # Rotate if needed
            if log_path.exists() and log_path.stat().st_size > self.MAX_LOG_SIZE:
                self._rotate_logs()

            log_path.touch(exist_ok=True)
        except (OSError, PermissionError) as e:
            print(f"Warning: Could not create debug log file: {e}", file=sys.stderr)
            self.enabled = False

    def _rotate_logs(self):
        """Rotate log files (.log -> .log.1 -> .log.2)."""
        log_path = Path(self.log_file)

        # Remove oldest backup
        oldest = Path(f"{self.log_file}.{self.BACKUP_COUNT}")
        if oldest.exists():
            oldest.unlink()

        # Rotate existing backups
        for i in range(self.BACKUP_COUNT - 1, 0, -1):
            src = Path(f"{self.log_file}.{i}")
            dst = Path(f"{self.log_file}.{i + 1}")
            if src.exists():
                src.rename(dst)

        # Move current log to .1
        if log_path.exists():
            log_path.rename(Path(f"{self.log_file}.1"))

    def log(self, message: str):
        """Write a log message with timestamp.

        Args:
            message: The message to log
        """
        if not self.enabled:
            return

        timestamp = datetime.now().isoformat(timespec="milliseconds")
        log_line = f"[{timestamp}] {message}\n"

        with self._lock:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(log_line)
                    f.flush()
            except OSError as e:
                print(f"Warning: Failed to write to debug log: {e}", file=sys.stderr)

    def log_section(self, title: str):
        """Log a section header.

        Args:
            title: Section title
        """
        if not self.enabled:
            return

        self.log("=" * 80)
        self.log(f"  {title}")
        self.log("=" * 80)

    def log_dict(self, data: dict, indent: int = 0):
        """Log a dictionary in readable format.

        Args:
            data: Dictionary to log
            indent: Indentation level
        """
        if not self.enabled:
            return

        prefix = "  " * indent
        for key, value in data.items():
            if isinstance(value, dict):
                self.log(f"{prefix}{key}:")
                self.log_dict(value, indent + 1)
            else:
                self.log(f"{prefix}{key}: {value}")


def get_python_version() -> str:
    """Get Python version info."""
    return f"{sys.version} ({sys.executable})"


def get_tmux_version() -> str:
    """Get tmux version."""
    try:
        result = subprocess.run(
            ["tmux", "-V"], capture_output=True, text=True, check=True, timeout=2
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def get_current_session_name() -> str:
    """Get the current session name."""
    try:
        result = subprocess.run(
            ["tmux", "display-message", "-p", "#{session_name}"],
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def get_current_window_index() -> str:
    """Get the current window index."""
    try:
        result = subprocess.run(
            ["tmux", "display-message", "-p", "#{window_index}"],
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def get_tmux_sessions() -> list:
    """Get list of all tmux sessions."""
    try:
        result = subprocess.run(
            ["tmux", "list-sessions", "-F", "#{session_name} #{session_windows}"],
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
        if result.returncode == 0:
            sessions = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split()
                    if len(parts) >= 2:
                        sessions.append({"name": parts[0], "windows": parts[1]})
            return sessions
        return []
    except Exception:
        return []


def get_tmux_windows() -> list:
    """Get list of windows in current session."""
    try:
        result = subprocess.run(
            ["tmux", "list-windows", "-F", "#{window_index} #{window_name} #{window_panes}"],
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
        if result.returncode == 0:
            windows = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split()
                    if len(parts) >= 3:
                        windows.append({"index": parts[0], "name": parts[1], "panes": parts[2]})
            return windows
        return []
    except Exception:
        return []


def get_tmux_panes() -> list:
    """Get list of panes in current window."""
    try:
        result = subprocess.run(
            [
                "tmux",
                "list-panes",
                "-F",
                "#{pane_id} #{pane_width} #{pane_height} #{pane_current_command}",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
        if result.returncode == 0:
            panes = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split()
                    if len(parts) >= 4:
                        panes.append(
                            {
                                "id": parts[0],
                                "width": parts[1],
                                "height": parts[2],
                                "command": parts[3],
                            }
                        )
            return panes
        return []
    except Exception:
        return []


def get_tmux_panes_with_positions() -> list:
    """Get list of panes with their positions in current window."""
    try:
        result = subprocess.run(
            [
                "tmux",
                "list-panes",
                "-F",
                "#{pane_id} #{pane_left} #{pane_top} #{pane_right} #{pane_bottom} #{pane_width} #{pane_height}",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
        if result.returncode == 0:
            panes = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split()
                    if len(parts) >= 7:
                        panes.append(
                            {
                                "id": parts[0],
                                "left": int(parts[1]),
                                "top": int(parts[2]),
                                "right": int(parts[3]),
                                "bottom": int(parts[4]),
                                "width": int(parts[5]),
                                "height": int(parts[6]),
                            }
                        )
            return panes
        return []
    except Exception:
        return []


def draw_pane_layout(panes_with_positions: list) -> list:
    """Draw an ASCII representation of the pane layout.

    Args:
        panes_with_positions: List of pane dicts with position info

    Returns:
        List of strings representing the ASCII layout
    """
    if not panes_with_positions:
        return ["No panes to display"]

    # Find window bounds
    max_right = max(p["right"] for p in panes_with_positions)
    max_bottom = max(p["bottom"] for p in panes_with_positions)

    # Scale factor to fit in reasonable ASCII width (aim for ~80 chars max)
    scale = 1
    if max_right > 78:
        scale = max_right / 78

    # Create a grid to draw the layout
    grid_width = int(max_right / scale) + 2
    grid_height = int(max_bottom / scale) + 2

    # Initialize grid with spaces
    grid = [[" " for _ in range(grid_width)] for _ in range(grid_height)]

    # Draw borders for each pane
    for pane in panes_with_positions:
        left = int(pane["left"] / scale)
        top = int(pane["top"] / scale)
        right = int(pane["right"] / scale)
        bottom = int(pane["bottom"] / scale)

        # Draw top and bottom borders
        for x in range(left, right + 1):
            if x < grid_width:
                if top < grid_height:
                    grid[top][x] = "─"
                if bottom < grid_height:
                    grid[bottom][x] = "─"

        # Draw left and right borders
        for y in range(top, bottom + 1):
            if y < grid_height:
                if left < grid_width:
                    grid[y][left] = "│"
                if right < grid_width:
                    grid[y][right] = "│"

        # Draw corners
        if top < grid_height and left < grid_width:
            grid[top][left] = "┌"
        if top < grid_height and right < grid_width:
            grid[top][right] = "┐"
        if bottom < grid_height and left < grid_width:
            grid[bottom][left] = "└"
        if bottom < grid_height and right < grid_width:
            grid[bottom][right] = "┘"

        # Add pane info in the center
        center_y = (top + bottom) // 2
        center_x = (left + right) // 2

        # Create pane label
        pane_label = f"{pane['id']} {pane['width']}x{pane['height']}"
        label_start = center_x - len(pane_label) // 2

        # Write label if it fits
        if center_y < grid_height and label_start >= left + 1:
            for i, char in enumerate(pane_label):
                x = label_start + i
                if x < right and x < grid_width:
                    grid[center_y][x] = char

    # Convert grid to strings
    return ["".join(row) for row in grid]
