"""Tests for pane_capture module."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from src.pane_capture import PaneCapture


class TestPaneCapture:
    """Test PaneCapture functionality."""

    def test_init(self):
        """Test PaneCapture initialization."""
        pane = PaneCapture("%0")
        assert pane.pane_id == "%0"

    @patch("subprocess.run")
    def test_capture_pane_success(self, mock_run):
        """Test successful pane capture."""
        mock_result = MagicMock()
        mock_result.stdout = "Line 1\nLine 2\nLine 3\n"
        mock_run.return_value = mock_result

        pane = PaneCapture("%0")
        result = pane.capture_pane()

        assert result == "Line 1\nLine 2\nLine 3\n"
        mock_run.assert_called_once_with(
            ["tmux", "capture-pane", "-p", "-e", "-t", "%0"],
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("subprocess.run")
    def test_capture_pane_with_ansi_codes(self, mock_run):
        """Test pane capture preserves ANSI codes."""
        mock_result = MagicMock()
        mock_result.stdout = "\033[1;31mRed text\033[0m\nNormal text\n"
        mock_run.return_value = mock_result

        pane = PaneCapture("%1")
        result = pane.capture_pane()

        assert result == "\033[1;31mRed text\033[0m\nNormal text\n"

    @patch("subprocess.run")
    def test_capture_pane_empty(self, mock_run):
        """Test capturing empty pane."""
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        pane = PaneCapture("%2")
        result = pane.capture_pane()

        assert result == ""

    @patch("subprocess.run")
    def test_capture_pane_error(self, mock_run):
        """Test pane capture with subprocess error."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "cmd", stderr="error")

        pane = PaneCapture("%0")

        with pytest.raises(RuntimeError, match="Failed to capture pane %0"):
            pane.capture_pane()

    @patch("subprocess.run")
    def test_get_pane_dimensions_success(self, mock_run):
        """Test successful get pane dimensions."""
        mock_result = MagicMock()
        mock_result.stdout = "80,24\n"
        mock_run.return_value = mock_result

        pane = PaneCapture("%0")
        result = pane.get_pane_dimensions()

        assert result == {"width": 80, "height": 24}
        mock_run.assert_called_once_with(
            [
                "tmux",
                "display-message",
                "-t",
                "%0",
                "-p",
                "#{pane_width},#{pane_height}",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("subprocess.run")
    def test_get_pane_dimensions_small_pane(self, mock_run):
        """Test get dimensions for small pane."""
        mock_result = MagicMock()
        mock_result.stdout = "40,10\n"
        mock_run.return_value = mock_result

        pane = PaneCapture("%1")
        result = pane.get_pane_dimensions()

        assert result == {"width": 40, "height": 10}

    @patch("subprocess.run")
    def test_get_pane_dimensions_large_pane(self, mock_run):
        """Test get dimensions for large pane."""
        mock_result = MagicMock()
        mock_result.stdout = "200,60\n"
        mock_run.return_value = mock_result

        pane = PaneCapture("%2")
        result = pane.get_pane_dimensions()

        assert result == {"width": 200, "height": 60}

    @patch("subprocess.run")
    def test_get_pane_dimensions_error(self, mock_run):
        """Test get pane dimensions with subprocess error."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "cmd", stderr="error")

        pane = PaneCapture("%0")

        with pytest.raises(RuntimeError, match="Failed to get pane dimensions"):
            pane.get_pane_dimensions()

    @patch("subprocess.run")
    def test_capture_pane_different_pane_ids(self, mock_run):
        """Test capture with different pane IDs."""
        mock_result = MagicMock()
        mock_result.stdout = "content"
        mock_run.return_value = mock_result

        # Test with various pane ID formats
        for pane_id in ["%0", "%1", "%10", "%100"]:
            pane = PaneCapture(pane_id)
            pane.capture_pane()

            # Verify the pane ID was used correctly in the call
            call_args = mock_run.call_args[0][0]
            assert call_args[-1] == pane_id
