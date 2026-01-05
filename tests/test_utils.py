"""Tests for utils module."""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.utils import FileUtils, PaneDimensions, SubprocessUtils, TmuxPaneUtils


class TestFileUtils:
    """Test FileUtils functionality."""

    def test_cleanup_dir_removes_existing_directory(self):
        """Test cleanup_dir removes an existing directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test_cleanup"
            test_dir.mkdir()
            test_file = test_dir / "test.txt"
            test_file.write_text("test content")

            assert test_dir.exists()
            result = FileUtils.cleanup_dir(str(test_dir))

            assert result is True
            assert not test_dir.exists()

    def test_cleanup_dir_succeeds_for_nonexistent_directory(self):
        """Test cleanup_dir succeeds when directory doesn't exist."""
        result = FileUtils.cleanup_dir("/nonexistent/path/to/directory")
        assert result is True

    def test_cleanup_dir_handles_permission_error(self):
        """Test cleanup_dir handles permission errors gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test_cleanup"
            test_dir.mkdir()

            with patch("src.utils.shutil.rmtree", side_effect=PermissionError("No permission")):
                result = FileUtils.cleanup_dir(str(test_dir))
                assert result is False

    def test_cleanup_dir_handles_os_error(self):
        """Test cleanup_dir handles OS errors gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test_cleanup"
            test_dir.mkdir()

            with patch("src.utils.shutil.rmtree", side_effect=OSError("OS error")):
                result = FileUtils.cleanup_dir(str(test_dir))
                assert result is False


class TestSubprocessUtils:
    """Test SubprocessUtils functionality."""

    def test_run_command_success(self):
        """Test run_command with successful command."""
        result = SubprocessUtils.run_command(["echo", "hello"])
        assert result == "hello"

    def test_run_command_with_default_on_failure(self):
        """Test run_command returns default on command failure."""
        result = SubprocessUtils.run_command(["false"], default="default_value", timeout=1)
        assert result == "default_value"

    def test_run_command_with_custom_default(self):
        """Test run_command with custom default value."""
        result = SubprocessUtils.run_command(
            ["nonexistent_command_xyz"], default="custom_default", timeout=1
        )
        assert result == "custom_default"

    def test_run_command_strips_whitespace(self):
        """Test run_command strips whitespace from output."""
        result = SubprocessUtils.run_command(["echo", "  hello  "])
        assert result == "hello"

    def test_run_command_timeout(self):
        """Test run_command handles timeout."""
        result = SubprocessUtils.run_command(["sleep", "10"], default="timeout", timeout=1)
        assert result == "timeout"

    def test_run_command_no_capture_output(self):
        """Test run_command with capture_output=False."""
        result = SubprocessUtils.run_command(["echo", "hello"], capture_output=False)
        assert result == ""

    def test_run_command_quiet_success(self):
        """Test run_command_quiet with successful command."""
        result = SubprocessUtils.run_command_quiet(["true"])
        assert result is True

    def test_run_command_quiet_failure(self):
        """Test run_command_quiet with failed command."""
        result = SubprocessUtils.run_command_quiet(["false"])
        assert result is False

    def test_run_command_quiet_nonexistent_command(self):
        """Test run_command_quiet with nonexistent command."""
        result = SubprocessUtils.run_command_quiet(["nonexistent_command_xyz"])
        assert result is False

    def test_run_command_quiet_timeout(self):
        """Test run_command_quiet handles timeout."""
        result = SubprocessUtils.run_command_quiet(["sleep", "10"], timeout=1)
        assert result is False

    def test_run_command_with_input_success(self):
        """Test run_command_with_input with successful command."""
        # Using 'cat' which reads stdin and writes to stdout
        result = SubprocessUtils.run_command_with_input(["cat"], "test input")
        assert result is True

    def test_run_command_with_input_failure(self):
        """Test run_command_with_input with failed command."""
        result = SubprocessUtils.run_command_with_input(["false"], "test input")
        assert result is False

    def test_run_command_with_input_nonexistent_command(self):
        """Test run_command_with_input with nonexistent command."""
        result = SubprocessUtils.run_command_with_input(["nonexistent_command_xyz"], "test input")
        assert result is False

    def test_run_command_with_input_timeout(self):
        """Test run_command_with_input handles timeout."""
        result = SubprocessUtils.run_command_with_input(["sleep", "10"], "test input", timeout=1)
        assert result is False

    def test_run_command_with_input_unicode(self):
        """Test run_command_with_input handles unicode."""
        result = SubprocessUtils.run_command_with_input(["cat"], "test unicode: 你好")
        assert result is True


class TestPaneDimensions:
    """Test PaneDimensions dataclass."""

    def test_pane_dimensions_creation(self):
        """Test creating a PaneDimensions instance."""
        pane = PaneDimensions(
            pane_id="%0",
            left=0,
            top=0,
            right=79,
            bottom=23,
            width=80,
            height=24,
        )

        assert pane.pane_id == "%0"
        assert pane.left == 0
        assert pane.top == 0
        assert pane.right == 79
        assert pane.bottom == 23
        assert pane.width == 80
        assert pane.height == 24


class TestTmuxPaneUtils:
    """Test TmuxPaneUtils functionality."""

    @patch("subprocess.run")
    def test_get_pane_dimensions_success(self, mock_run):
        """Test get_pane_dimensions with successful tmux command."""
        mock_result = MagicMock()
        mock_result.stdout = "%0 0 0 79 23 80 24\n"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = TmuxPaneUtils.get_pane_dimensions("%0")

        assert result is not None
        assert result.pane_id == "%0"
        assert result.left == 0
        assert result.top == 0
        assert result.right == 79
        assert result.bottom == 23
        assert result.width == 80
        assert result.height == 24

    @patch("subprocess.run")
    def test_get_pane_dimensions_with_offset_pane(self, mock_run):
        """Test get_pane_dimensions with pane that has offset position."""
        mock_result = MagicMock()
        mock_result.stdout = "%1 40 12 119 35 80 24\n"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = TmuxPaneUtils.get_pane_dimensions("%1")

        assert result is not None
        assert result.pane_id == "%1"
        assert result.left == 40
        assert result.top == 12
        assert result.right == 119
        assert result.bottom == 35
        assert result.width == 80
        assert result.height == 24

    @patch("subprocess.run")
    def test_get_pane_dimensions_subprocess_error(self, mock_run):
        """Test get_pane_dimensions handles subprocess errors."""
        mock_run.side_effect = subprocess.SubprocessError("Command failed")

        result = TmuxPaneUtils.get_pane_dimensions("%0")

        assert result is None

    @patch("subprocess.run")
    def test_get_pane_dimensions_invalid_output(self, mock_run):
        """Test get_pane_dimensions handles invalid output."""
        mock_result = MagicMock()
        mock_result.stdout = "invalid output\n"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = TmuxPaneUtils.get_pane_dimensions("%0")

        assert result is None

    @patch("subprocess.run")
    def test_get_pane_dimensions_wrong_number_of_fields(self, mock_run):
        """Test get_pane_dimensions handles wrong number of fields."""
        mock_result = MagicMock()
        mock_result.stdout = "%0 0 0 79 23\n"  # Missing width and height
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = TmuxPaneUtils.get_pane_dimensions("%0")

        assert result is None

    @patch("subprocess.run")
    def test_get_pane_dimensions_timeout(self, mock_run):
        """Test get_pane_dimensions handles timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 2)

        result = TmuxPaneUtils.get_pane_dimensions("%0")

        assert result is None

    def test_calculate_popup_position_top_pane(self):
        """Test calculate_popup_position for pane at top (top=0)."""
        dimensions = PaneDimensions(
            pane_id="%0",
            left=0,
            top=0,
            right=79,
            bottom=23,
            width=80,
            height=24,
        )

        result = TmuxPaneUtils.calculate_popup_position(dimensions)

        assert result == {
            "x": 0,
            "y": 0,  # For top panes, y = top
            "width": 80,
            "height": 24,
        }

    def test_calculate_popup_position_non_top_pane(self):
        """Test calculate_popup_position for pane not at top (top>0)."""
        dimensions = PaneDimensions(
            pane_id="%1",
            left=40,
            top=12,
            right=119,
            bottom=35,
            width=80,
            height=24,
        )

        result = TmuxPaneUtils.calculate_popup_position(dimensions)

        assert result == {
            "x": 40,
            "y": 36,  # For non-top panes, y = bottom + 1
            "width": 80,
            "height": 24,
        }

    def test_calculate_popup_position_left_offset_pane(self):
        """Test calculate_popup_position for pane with left offset."""
        dimensions = PaneDimensions(
            pane_id="%2",
            left=20,
            top=0,
            right=99,
            bottom=23,
            width=80,
            height=24,
        )

        result = TmuxPaneUtils.calculate_popup_position(dimensions)

        assert result == {
            "x": 20,
            "y": 0,
            "width": 80,
            "height": 24,
        }

    def test_calculate_popup_position_small_pane(self):
        """Test calculate_popup_position for small pane."""
        dimensions = PaneDimensions(
            pane_id="%3",
            left=10,
            top=5,
            right=29,
            bottom=14,
            width=20,
            height=10,
        )

        result = TmuxPaneUtils.calculate_popup_position(dimensions)

        assert result == {
            "x": 10,
            "y": 15,  # bottom + 1
            "width": 20,
            "height": 10,
        }
