#!/usr/bin/env python3
"""
tmux-flash-copy: A tmux plugin for flash-like searching and copying.

Inspired by flash.nvim, this plugin allows you to search visible text in the
current tmux pane, label it with keyboard shortcuts, and copy it to the clipboard.
"""

import subprocess
import sys
from pathlib import Path

# Add parent directory to path for imports
PLUGIN_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PLUGIN_DIR))

from src.clipboard import Clipboard  # noqa: E402
from src.config import ConfigLoader  # noqa: E402
from src.debug_logger import (  # noqa: E402
    DebugLogger,
    draw_pane_layout,
    get_current_session_name,
    get_current_window_index,
    get_python_version,
    get_tmux_panes,
    get_tmux_panes_with_positions,
    get_tmux_sessions,
    get_tmux_version,
    get_tmux_windows,
)
from src.pane_capture import PaneCapture  # noqa: E402
from src.popup_ui import PopupUI  # noqa: E402
from src.search_interface import SearchInterface  # noqa: E402


def get_tmux_pane_id():
    """Get the current active tmux pane ID."""
    try:
        result = subprocess.run(
            ["tmux", "display-message", "-p", "#{pane_id}"],
            capture_output=True,
            text=True,
            check=True,
        )
        pane_id = result.stdout.strip()
        return pane_id
    except subprocess.CalledProcessError as e:
        error_msg = f"Error getting pane ID: {e}"
        print(error_msg, file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point for the tmux-flash-copy plugin."""
    try:
        # Get the current pane ID
        pane_id = get_tmux_pane_id()

        # Capture pane contents
        capture = PaneCapture(pane_id)
        pane_content = capture.capture_pane()

        # Load all configuration from tmux
        config = ConfigLoader.load_all_flash_copy_config()

        # Initialize debug logger if enabled
        if config.debug_enabled:
            logger = DebugLogger.get_instance(enabled=True)
            logger.log_section("TMUX-FLASH-COPY DEBUG SESSION STARTED")

            # Log environment info
            logger.log(f"Python: {get_python_version()}")
            logger.log(f"Tmux: {get_tmux_version()}")
            logger.log(f"Pane ID: {pane_id}")
            logger.log(f"Log file: {logger.log_file}")

            # Log all configuration
            logger.log_section("Configuration Settings")
            logger.log_dict(
                {
                    "auto_paste": config.auto_paste,
                    "reverse_search": config.reverse_search,
                    "case_sensitive": config.case_sensitive,
                    "word_separators": repr(config.word_separators)
                    if config.word_separators
                    else "(default)",
                    "prompt_position": config.prompt_position,
                    "prompt_indicator": config.prompt_indicator,
                    "prompt_placeholder_text": config.prompt_placeholder_text,
                    "highlight_colour": repr(config.highlight_colour),
                    "label_colour": repr(config.label_colour),
                    "prompt_colour": repr(config.prompt_colour),
                    "debug_enabled": config.debug_enabled,
                }
            )

            # Log tmux environment
            logger.log_section("Tmux Environment")

            # Get current active items
            current_session = get_current_session_name()
            current_window = get_current_window_index()
            current_pane = pane_id

            sessions = get_tmux_sessions()
            logger.log(f"Sessions ({len(sessions)}):")
            for session in sessions:
                marker = " ← ACTIVE" if session["name"] == current_session else ""
                logger.log(f"  - {session['name']} ({session['windows']} windows){marker}")

            windows = get_tmux_windows()
            logger.log(f"Windows ({len(windows)}):")
            for window in windows:
                marker = " ← ACTIVE" if window["index"] == current_window else ""
                logger.log(
                    f"  - [{window['index']}] {window['name']} ({window['panes']} panes){marker}"
                )

            panes = get_tmux_panes()
            logger.log(f"Panes ({len(panes)}):")
            for pane in panes:
                marker = " ← ACTIVE" if pane["id"] == current_pane else ""
                logger.log(
                    f"  - {pane['id']}: {pane['width']}x{pane['height']} ({pane['command']}){marker}"
                )

            # Draw ASCII pane layout
            logger.log_section("Pane Layout (ASCII)")
            panes_with_positions = get_tmux_panes_with_positions()
            layout_lines = draw_pane_layout(panes_with_positions)
            for line in layout_lines:
                logger.log(line)

            # Log pane dimensions for popup positioning
            dimensions = capture.get_pane_dimensions()
            if dimensions:
                logger.log_section("Current Pane Dimensions (for popup positioning)")
                logger.log_dict(dimensions)

        # Initialise search interface with config options
        search = SearchInterface(
            pane_content,
            reverse_search=config.reverse_search,
            word_separators=config.word_separators,
            case_sensitive=config.case_sensitive,
        )

        # Initialise clipboard helper
        clipboard = Clipboard()

        # Initialise popup UI
        ui = PopupUI(
            pane_content=pane_content,
            search_interface=search,
            clipboard=clipboard,
            pane_id=pane_id,
            config=config,
        )

        # Run the interactive search interface
        result, should_paste = ui.run()

        if result:
            # Copy to clipboard and optionally paste
            logger = DebugLogger.get_instance() if config.debug_enabled else None
            clipboard.copy_and_paste(
                result, pane_id=pane_id, auto_paste=should_paste, logger=logger
            )

    except KeyboardInterrupt:
        print("\nSearch cancelled", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        import traceback

        error_msg = f"Error: {e}\n{traceback.format_exc()}"
        print(error_msg, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
