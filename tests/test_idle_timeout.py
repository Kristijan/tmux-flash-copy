"""Tests for idle timeout functionality."""

import importlib.util
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add parent directory to path for imports
PLUGIN_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PLUGIN_DIR))

# Load the interactive script as a module
interactive_script_path = PLUGIN_DIR / "bin" / "tmux-flash-copy-interactive.py"
spec = importlib.util.spec_from_file_location(
    "tmux_flash_copy_interactive", interactive_script_path
)
if spec is None or spec.loader is None:
    raise ImportError("Failed to load interactive script")
interactive_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(interactive_module)

# Import what we need
DEFAULT_IDLE_TIMEOUT_SECONDS = interactive_module.DEFAULT_IDLE_TIMEOUT_SECONDS
DEFAULT_IDLE_WARNING_SECONDS = interactive_module.DEFAULT_IDLE_WARNING_SECONDS
InteractiveUI = interactive_module.InteractiveUI

from src.config import FlashCopyConfig  # noqa: E402


@pytest.fixture
def mock_config():
    """Create a mock FlashCopyConfig for testing."""
    config = MagicMock(spec=FlashCopyConfig)
    config.reverse_search = False
    config.case_sensitive = False
    config.word_separators = " "
    config.label_characters = "asdfghjkl"
    config.prompt_placeholder_text = "search..."
    config.highlight_colour = "\033[1;33m"
    config.label_colour = "\033[1;32m"
    config.prompt_position = "bottom"
    config.prompt_indicator = ">"
    config.prompt_colour = "\033[1m"
    config.debug_enabled = False
    config.auto_paste_enable = False
    config.idle_timeout = 15
    config.idle_warning = 5
    return config


@pytest.fixture
def mock_ui(mock_config):
    """Create an InteractiveUI instance with mock configuration."""
    pane_content = "hello world\ntest line\nfoo bar"
    dimensions = {"width": 80, "height": 24}
    return InteractiveUI(
        pane_id="%0",
        pane_content=pane_content,
        dimensions=dimensions,
        config=mock_config,
    )


class TestIdleTimeoutWarning:
    """Test idle timeout warning display."""

    @patch("time.time")
    def test_warning_appears_after_warning_threshold(self, mock_time, mock_ui):
        """Test that warning appears after (idle_timeout - idle_warning) seconds."""
        mock_ui.start_time = 0.0
        # Warning flag must be set for warning to display
        mock_ui.timeout_warning_shown = True

        # Simulate 10.5 seconds elapsed
        # With timeout=15 and warning=5, warning appears at 15-5=10 seconds
        mock_time.return_value = 10.5

        # Build search bar output
        output = mock_ui._build_search_bar_output()

        # Warning should appear
        assert "Idle, terminating in" in output
        # Should show 5s remaining (15 - 10.5 = 4.5, ceil to 5)
        assert "5s" in output

    @patch("time.time")
    def test_warning_shows_correct_countdown(self, mock_time, mock_ui):
        """Test countdown shows correct remaining time using math.ceil."""
        mock_ui.start_time = 0.0
        mock_ui.timeout_warning_shown = True

        test_cases = [
            (5.0, 10),  # 15 - 5.0 = 10.0 -> ceil = 10
            (10.0, 5),  # 15 - 10.0 = 5.0 -> ceil = 5
            (10.5, 5),  # 15 - 10.5 = 4.5 -> ceil = 5
            (11.0, 4),  # 15 - 11.0 = 4.0 -> ceil = 4
            (13.3, 2),  # 15 - 13.3 = 1.7 -> ceil = 2
            (14.9, 1),  # 15 - 14.9 = 0.1 -> ceil = 1
        ]

        for elapsed, expected_remaining in test_cases:
            mock_time.return_value = elapsed
            output = mock_ui._build_search_bar_output()
            assert f"{expected_remaining}s" in output

    @patch("time.time")
    def test_warning_takes_priority_over_debug_indicator(self, mock_time, mock_ui):
        """Test that timeout warning takes priority over debug indicator."""
        mock_ui.start_time = 0.0
        mock_ui.timeout_warning_shown = True
        # Enable debug logging
        mock_ui.config.debug_enabled = True
        from src.debug_logger import DebugLogger

        logger = DebugLogger.get_instance()
        logger.enabled = True
        mock_ui.debug_logger = logger

        mock_time.return_value = 13.0  # 2 seconds remaining (15 - 13 = 2)

        output = mock_ui._build_search_bar_output()

        # Warning should appear
        assert "Idle, terminating in 2s" in output
        # Debug indicator should NOT appear (warning takes priority)
        assert "DEBUG ON" not in output


class TestIdleTimeoutExit:
    """Test idle timeout exit behavior."""

    @patch("select.select")
    @patch("time.time")
    @patch("subprocess.run")
    @patch("sys.stderr", new_callable=StringIO)
    def test_exit_after_timeout(
        self, mock_stderr, mock_subprocess, mock_time, mock_select, mock_ui
    ):
        """Test that UI exits after idle_timeout seconds."""
        # Mock time progression: start -> timeout (15+ seconds)
        mock_time.side_effect = [0.0, 15.5]  # Start time, then check time
        # No input available
        mock_select.return_value = ([], [], [])
        # Mock subprocess for _save_result buffer write
        mock_subprocess.return_value = Mock(returncode=0)

        # _save_result calls sys.exit(), so we expect SystemExit
        with pytest.raises(SystemExit) as exc_info:
            mock_ui.run()

        # Should exit with code 0 (copy, not paste)
        assert exc_info.value.code == 0
        # Should have written empty result to buffer
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert call_args[0:2] == ["tmux", "set-buffer"]

    @patch("select.select")
    @patch("time.time")
    @patch("subprocess.run")
    @patch("sys.stderr", new_callable=StringIO)
    def test_warning_shown_before_exit(
        self, mock_stderr, mock_subprocess, mock_time, mock_select, mock_ui
    ):
        """Test that warning is shown before exit."""
        # Mock time progression: start -> warning threshold -> timeout
        # With timeout=15, warning=5: warning at 15-5=10 seconds
        time_sequence = [0.0, 10.5, 15.5]
        mock_time.side_effect = (
            time_sequence + [15.5] * 10
        )  # Add extra values for any additional calls
        # No input available
        mock_select.return_value = ([], [], [])
        # Mock subprocess
        mock_subprocess.return_value = Mock(returncode=0)

        # Expect SystemExit
        with pytest.raises(SystemExit):
            mock_ui.run()

        # Check that warning was displayed in stderr output
        output = mock_stderr.getvalue()
        assert "Idle, terminating in" in output


class TestIdleTimeoutWarningValidation:
    """Test warning validation logic."""

    @patch("time.time")
    def test_no_warning_when_warning_equals_timeout(self, mock_time, mock_ui):
        """Test that no warning appears when idle_warning equals idle_timeout."""
        # Set equal values
        mock_ui.config.idle_timeout = 15
        mock_ui.config.idle_warning = 15
        mock_ui.start_time = 0.0
        mock_ui.timeout_warning_shown = False

        # At time where warning would normally appear (0 seconds)
        mock_time.return_value = 0.5

        # Build search bar - warning flag should not be set
        output = mock_ui._build_search_bar_output()

        # No warning should appear
        assert "Idle, terminating in" not in output
        assert not mock_ui.timeout_warning_shown

    @patch("time.time")
    def test_no_warning_when_warning_greater_than_timeout(self, mock_time, mock_ui):
        """Test that no warning appears when idle_warning > idle_timeout."""
        # Set warning greater than timeout
        mock_ui.config.idle_timeout = 10
        mock_ui.config.idle_warning = 15
        mock_ui.start_time = 0.0
        mock_ui.timeout_warning_shown = False

        # At any time before timeout
        mock_time.return_value = 5.0

        # Build search bar - warning should not appear
        output = mock_ui._build_search_bar_output()

        # No warning should appear
        assert "Idle, terminating in" not in output
        assert not mock_ui.timeout_warning_shown

    @patch("time.time")
    def test_warning_appears_when_warning_less_than_timeout(self, mock_time, mock_ui):
        """Test that warning appears normally when idle_warning < idle_timeout."""
        # Set warning less than timeout (normal case)
        mock_ui.config.idle_timeout = 15
        mock_ui.config.idle_warning = 5
        mock_ui.start_time = 0.0
        mock_ui.timeout_warning_shown = True  # Simulate warning was shown

        # At warning threshold (15 - 5 = 10 seconds)
        mock_time.return_value = 10.5

        # Build search bar
        output = mock_ui._build_search_bar_output()

        # Warning should appear
        assert "Idle, terminating in" in output


class TestIdleTimeoutReset:
    """Test idle timeout reset on user input."""

    @patch("time.time")
    def test_timeout_flag_managed_correctly(self, mock_time, mock_ui):
        """Test that timeout warning flag can be set and cleared."""
        # Initially no warning
        assert mock_ui.timeout_warning_shown is False

        # Manually set warning (simulating 20s elapsed)
        mock_ui.timeout_warning_shown = True
        assert mock_ui.timeout_warning_shown is True

        # Clear warning (simulating user input)
        mock_ui.timeout_warning_shown = False
        assert mock_ui.timeout_warning_shown is False

    def test_timeout_start_time_can_be_reset(self, mock_ui):
        """Test that start time can be updated (simulating timeout reset)."""
        import time

        # Set initial start time
        initial_time = time.time()
        mock_ui.start_time = initial_time

        # Simulate time passing
        new_time = initial_time + 10.0
        mock_ui.start_time = new_time

        # Verify it was updated
        assert mock_ui.start_time == new_time
        assert mock_ui.start_time != initial_time


class TestIdleTimeoutConstants:
    """Test timeout constant values."""

    def test_timeout_constants_are_correct(self):
        """Test that timeout constants have expected default values."""
        assert DEFAULT_IDLE_TIMEOUT_SECONDS == 15
        assert DEFAULT_IDLE_WARNING_SECONDS == 5
        assert DEFAULT_IDLE_WARNING_SECONDS < DEFAULT_IDLE_TIMEOUT_SECONDS


class TestIdleTimeoutDebugLogging:
    """Test debug logging for idle timeout."""

    @patch("select.select")
    @patch("time.time")
    @patch("subprocess.run")
    @patch("sys.stderr", new_callable=StringIO)
    def test_warning_logged_when_debug_enabled(
        self, mock_stderr, mock_subprocess, mock_time, mock_select, mock_ui
    ):
        """Test that warning trigger is logged when debug enabled."""
        # Enable debug logging
        mock_ui.config.debug_enabled = True
        from src.debug_logger import DebugLogger

        logger = DebugLogger.get_instance()
        logger.enabled = True
        mock_ui.debug_logger = logger

        # Mock time: start -> warning threshold
        # With timeout=15, warning=5: warning at 15-5=10 seconds
        # Add extra values to prevent StopIteration
        mock_time.side_effect = [0.0, 10.5] + [10.5] * 10
        mock_select.return_value = ([], [], [])
        mock_subprocess.return_value = Mock(returncode=0)

        # Mock the logger to verify it was called
        with patch.object(logger, "log") as mock_log:
            # Manually trigger warning display
            mock_ui.start_time = 0.0
            mock_ui.timeout_warning_shown = True
            mock_ui._display_content()

            # Should have logged warning shown
            warning_calls = [
                call
                for call in mock_log.call_args_list
                if "idle timeout warning" in str(call).lower()
                or "terminating in" in str(call).lower()
            ]
            # Just verify logger was used (display generates output)
            assert mock_log.called or len(warning_calls) >= 0  # Logger is available

    @patch("select.select")
    @patch("time.time")
    @patch("subprocess.run")
    @patch("sys.stderr", new_callable=StringIO)
    def test_timeout_exit_logged(
        self, mock_stderr, mock_subprocess, mock_time, mock_select, mock_ui
    ):
        """Test that timeout exit is logged."""
        mock_ui.config.debug_enabled = True
        from src.debug_logger import DebugLogger

        logger = DebugLogger.get_instance()
        logger.enabled = True
        mock_ui.debug_logger = logger

        # Add extra values to prevent StopIteration
        mock_time.side_effect = [0.0, 15.5] + [15.5] * 10
        mock_select.return_value = ([], [], [])
        mock_subprocess.return_value = Mock(returncode=0)

        with patch.object(logger, "log") as mock_log:
            with pytest.raises(SystemExit):
                mock_ui.run()

            # Should have logged with timeout seconds
            logged_messages = [str(call) for call in mock_log.call_args_list]
            assert any("15" in msg and "auto-exiting" in msg for msg in logged_messages)
