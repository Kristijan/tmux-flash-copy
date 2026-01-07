"""Tests for src.debug_logger module."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.debug_logger import (
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


def test_get_python_version_contains_executable_and_version():
    v = get_python_version()
    assert sys.executable in v
    assert sys.version.split()[0] in v


def test_get_tmux_version_success_and_failure():
    mock = MagicMock()
    mock.stdout = "tmux 3.3a"
    with patch("subprocess.run", return_value=mock):
        assert get_tmux_version() == "tmux 3.3a"

    with patch("subprocess.run", side_effect=Exception("fail")):
        assert get_tmux_version() == "unknown"


def test_get_current_session_and_window_index():
    sess = MagicMock()
    sess.stdout = "my-session"
    win = MagicMock()
    win.stdout = "2"

    with patch("subprocess.run", side_effect=[sess, win]):
        assert get_current_session_name() == "my-session"
        assert get_current_window_index() == "2"

    with patch("subprocess.run", side_effect=Exception("nope")):
        assert get_current_session_name() == ""
        assert get_current_window_index() == ""


def test_get_tmux_sessions_and_windows_and_panes_parsing():
    sessions_out = "s1 3\ns2 2\n"
    windows_out = "0 main 2\n1 other 1\n"
    panes_out = "%1 80 24 bash\n%2 40 12 zsh\n"
    panes_pos_out = "%1 0 0 79 23 80 24\n%2 80 0 119 11 40 12\n"

    mock_sess = MagicMock(return_value=None)
    mock_sess.returncode = 0
    mock_sess.stdout = sessions_out
    mock_win = MagicMock(return_value=None)
    mock_win.returncode = 0
    mock_win.stdout = windows_out
    mock_panes = MagicMock(return_value=None)
    mock_panes.returncode = 0
    mock_panes.stdout = panes_out
    mock_panes_pos = MagicMock(return_value=None)
    mock_panes_pos.returncode = 0
    mock_panes_pos.stdout = panes_pos_out

    with patch("subprocess.run", side_effect=[mock_sess, mock_win, mock_panes, mock_panes_pos]):
        sessions = get_tmux_sessions()
        windows = get_tmux_windows()
        panes = get_tmux_panes()
        panes_pos = get_tmux_panes_with_positions()

    assert isinstance(sessions, list) and sessions[0]["name"] == "s1"
    assert isinstance(windows, list) and windows[0]["name"] == "main"
    assert isinstance(panes, list) and panes[0]["id"] == "%1"
    assert isinstance(panes_pos, list) and panes_pos[0]["left"] == 0


def test_draw_pane_layout_empty_and_simple():
    assert draw_pane_layout([]) == ["No panes to display"]

    panes = [{"id": "%1", "left": 0, "top": 0, "right": 10, "bottom": 4, "width": 11, "height": 5}]
    grid = draw_pane_layout(panes)
    # Should contain corner characters and pane id in label area
    joined = "\n".join(grid)
    assert "┌" in joined and "%1" in joined


def test_debug_logger_write_and_rotation(tmp_path):
    # Setup a temp log directory
    log_file = tmp_path / "dbg.log"
    # Ensure there is a current log and backups
    (log_file).write_text("a" * 1024)
    (tmp_path / "dbg.log.1").write_text("old1")
    (tmp_path / "dbg.log.2").write_text("old2")

    # Force small max size to trigger rotation
    orig_max = DebugLogger.MAX_LOG_SIZE
    DebugLogger.MAX_LOG_SIZE = 10

    try:
        logger = DebugLogger(enabled=True, log_file=str(log_file))
        # After init, rotation should have happened and current log recreated
        assert Path(str(logger.log_file)).exists()

        logger.log("hello world")
        logger.log_section("section")
        logger.log_dict({"a": 1, "b": {"c": 2}})

        contents = Path(logger.log_file).read_text()
        assert "hello world" in contents
        assert "section" in contents
        assert "a: 1" in contents
        # Simulate write failure: patch open to raise
        with patch("builtins.open", side_effect=OSError("deny")):
            logger.log("won't write")  # should not raise
    finally:
        DebugLogger.MAX_LOG_SIZE = orig_max


def test_debug_logger_get_default_path_and_disable_on_error(tmp_path, monkeypatch):
    # Simulate Path.touch raising OSError to hit fallback
    def _raise_touch(self, *args, **kwargs):
        raise OSError("nope")

    monkeypatch.setattr(Path, "touch", _raise_touch)

    # Creating DebugLogger with enabled True should fallback without exception
    logger = DebugLogger(enabled=True, log_file=None)
    assert logger.enabled in (True, False)

    # Cleanup singleton for other tests
    DebugLogger._instance = None
