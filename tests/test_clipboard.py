"""Tests for clipboard module."""

import sys
from unittest.mock import MagicMock, patch

from src.clipboard import Clipboard


class TestClipboard:
    """Test Clipboard functionality."""

    def test_copy_fails_without_tmux_env(self, no_tmux_env):
        """Test copy fails when TMUX environment variable is not set."""
        result = Clipboard.copy("test text")
        assert result is False

    @patch("src.clipboard.Clipboard._tmux_osc52")
    def test_copy_success_with_osc52(self, mock_osc52, mock_tmux_env):
        """Test successful copy using tmux OSC52."""
        mock_osc52.return_value = True

        result = Clipboard.copy("test text")

        assert result is True
        mock_osc52.assert_called_once_with("test text")

    @patch("src.clipboard.Clipboard._tmux_osc52")
    @patch("src.clipboard.Clipboard._pbcopy")
    def test_copy_fallback_to_pbcopy_on_macos(self, mock_pbcopy, mock_osc52, mock_tmux_env):
        """Test fallback to pbcopy when OSC52 fails on macOS."""
        mock_osc52.return_value = False
        mock_pbcopy.return_value = True

        with patch.object(sys, "platform", "darwin"):
            result = Clipboard.copy("test text")

        assert result is True
        mock_osc52.assert_called_once()
        mock_pbcopy.assert_called_once_with("test text")

    @patch("src.clipboard.Clipboard._tmux_osc52")
    @patch("src.clipboard.Clipboard._xclip")
    def test_copy_fallback_to_xclip_on_linux(self, mock_xclip, mock_osc52, mock_tmux_env):
        """Test fallback to xclip when OSC52 fails on Linux."""
        mock_osc52.return_value = False
        mock_xclip.return_value = True

        with patch.object(sys, "platform", "linux"):
            result = Clipboard.copy("test text")

        assert result is True
        mock_osc52.assert_called_once()
        mock_xclip.assert_called_once_with("test text")

    @patch("src.clipboard.Clipboard._tmux_osc52")
    @patch("src.clipboard.Clipboard._xclip")
    @patch("src.clipboard.Clipboard._xsel")
    def test_copy_fallback_to_xsel_on_linux(self, mock_xsel, mock_xclip, mock_osc52, mock_tmux_env):
        """Test fallback to xsel when both OSC52 and xclip fail on Linux."""
        mock_osc52.return_value = False
        mock_xclip.return_value = False
        mock_xsel.return_value = True

        with patch.object(sys, "platform", "linux"):
            result = Clipboard.copy("test text")

        assert result is True
        mock_osc52.assert_called_once()
        mock_xclip.assert_called_once()
        mock_xsel.assert_called_once_with("test text")

    @patch("src.clipboard.Clipboard._tmux_osc52")
    @patch("src.clipboard.Clipboard._pbcopy")
    @patch("src.clipboard.Clipboard._tmux_buffer")
    def test_copy_fallback_to_tmux_buffer(
        self, mock_tmux_buffer, mock_pbcopy, mock_osc52, mock_tmux_env
    ):
        """Test fallback to tmux buffer when all clipboard methods fail."""
        mock_osc52.return_value = False
        mock_pbcopy.return_value = False
        mock_tmux_buffer.return_value = True

        with patch.object(sys, "platform", "darwin"):
            result = Clipboard.copy("test text")

        assert result is True
        mock_tmux_buffer.assert_called_once_with("test text")

    @patch("src.clipboard.Clipboard._tmux_osc52")
    @patch("src.clipboard.Clipboard._pbcopy")
    @patch("src.clipboard.Clipboard._tmux_buffer")
    def test_copy_all_methods_fail(self, mock_tmux_buffer, mock_pbcopy, mock_osc52, mock_tmux_env):
        """Test copy fails when all methods fail."""
        mock_osc52.return_value = False
        mock_pbcopy.return_value = False
        mock_tmux_buffer.return_value = False

        with patch.object(sys, "platform", "darwin"):
            result = Clipboard.copy("test text")

        assert result is False

    @patch("src.clipboard.Clipboard._tmux_osc52")
    def test_copy_with_logger(self, mock_osc52, mock_tmux_env):
        """Test copy with logger logs success."""
        mock_osc52.return_value = True
        mock_logger = MagicMock()

        result = Clipboard.copy("test text", logger=mock_logger)

        assert result is True
        mock_logger.log.assert_called_once_with("Clipboard: Success via tmux OSC52")

    @patch("src.clipboard.Clipboard._tmux_osc52")
    @patch("src.clipboard.Clipboard._pbcopy")
    def test_copy_with_logger_logs_fallback(self, mock_pbcopy, mock_osc52, mock_tmux_env):
        """Test copy with logger logs fallback method."""
        mock_osc52.return_value = False
        mock_pbcopy.return_value = True
        mock_logger = MagicMock()

        with patch.object(sys, "platform", "darwin"):
            result = Clipboard.copy("test text", logger=mock_logger)

        assert result is True
        mock_logger.log.assert_called_once_with("Clipboard: Success via pbcopy (macOS)")

    def test_copy_with_logger_logs_no_tmux(self, no_tmux_env):
        """Test copy with logger logs failure when not in tmux."""
        mock_logger = MagicMock()

        result = Clipboard.copy("test text", logger=mock_logger)

        assert result is False
        mock_logger.log.assert_called_once_with("Clipboard: Failed - not in tmux")

    @patch("src.clipboard.Clipboard.copy")
    def test_copy_and_paste_copy_fails(self, mock_copy, mock_tmux_env):
        """Test copy_and_paste fails when copy fails."""
        mock_copy.return_value = False

        result = Clipboard.copy_and_paste("test text", pane_id="%0")

        assert result is False

    @patch("src.clipboard.Clipboard.copy")
    @patch("src.clipboard.SubprocessUtils.run_command_quiet")
    def test_copy_and_paste_without_auto_paste(self, mock_run, mock_copy, mock_tmux_env):
        """Test copy_and_paste without auto_paste only copies."""
        mock_copy.return_value = True

        result = Clipboard.copy_and_paste("test text", pane_id="%0", auto_paste=False)

        assert result is True
        mock_copy.assert_called_once()
        mock_run.assert_not_called()

    @patch("src.clipboard.Clipboard.copy")
    @patch("src.clipboard.SubprocessUtils.run_command_quiet")
    def test_copy_and_paste_with_auto_paste(self, mock_run, mock_copy, mock_tmux_env):
        """Test copy_and_paste with auto_paste copies and pastes."""
        mock_copy.return_value = True
        mock_run.return_value = True

        result = Clipboard.copy_and_paste("test text", pane_id="%0", auto_paste=True)

        assert result is True
        mock_copy.assert_called_once()
        # Should be called twice: once for set-buffer, once for paste-buffer
        assert mock_run.call_count == 2

    @patch("src.clipboard.Clipboard.copy")
    @patch("src.clipboard.SubprocessUtils.run_command_quiet")
    def test_copy_and_paste_auto_paste_without_pane_id(self, mock_run, mock_copy, mock_tmux_env):
        """Test copy_and_paste with auto_paste but no pane_id only copies."""
        mock_copy.return_value = True

        result = Clipboard.copy_and_paste("test text", pane_id=None, auto_paste=True)

        assert result is True
        mock_copy.assert_called_once()
        mock_run.assert_not_called()

    @patch("src.clipboard.Clipboard.copy")
    @patch("src.clipboard.SubprocessUtils.run_command_quiet")
    def test_copy_and_paste_with_logger(self, mock_run, mock_copy, mock_tmux_env):
        """Test copy_and_paste with logger logs auto-paste success."""
        mock_copy.return_value = True
        mock_run.return_value = True
        mock_logger = MagicMock()

        result = Clipboard.copy_and_paste(
            "test text", pane_id="%0", auto_paste=True, logger=mock_logger
        )

        assert result is True
        # Should log the auto-paste success
        mock_logger.log.assert_called_with("Auto-paste to pane %0: Success")

    @patch("src.clipboard.Clipboard.copy")
    @patch("src.clipboard.SubprocessUtils.run_command_quiet")
    def test_copy_and_paste_paste_fails_silently(self, mock_run, mock_copy, mock_tmux_env):
        """Test copy_and_paste succeeds even if paste fails."""
        mock_copy.return_value = True
        mock_run.side_effect = Exception("Paste failed")

        result = Clipboard.copy_and_paste("test text", pane_id="%0", auto_paste=True)

        # Should still return True since copy succeeded
        assert result is True

    @patch("src.utils.SubprocessUtils.run_command_quiet")
    def test_tmux_osc52_method(self, mock_run):
        """Test _tmux_osc52 calls correct command."""
        mock_run.return_value = True

        result = Clipboard._tmux_osc52("test text")

        assert result is True
        mock_run.assert_called_once_with(["tmux", "set-buffer", "-w", "--", "test text"])

    @patch("src.utils.SubprocessUtils.run_command_with_input")
    def test_pbcopy_method(self, mock_run):
        """Test _pbcopy calls correct command."""
        mock_run.return_value = True

        result = Clipboard._pbcopy("test text")

        assert result is True
        mock_run.assert_called_once_with(["pbcopy"], "test text")

    @patch("src.utils.SubprocessUtils.run_command_with_input")
    def test_xclip_method(self, mock_run):
        """Test _xclip calls correct command."""
        mock_run.return_value = True

        result = Clipboard._xclip("test text")

        assert result is True
        mock_run.assert_called_once_with(["xclip", "-selection", "clipboard"], "test text")

    @patch("src.utils.SubprocessUtils.run_command_with_input")
    def test_xsel_method(self, mock_run):
        """Test _xsel calls correct command."""
        mock_run.return_value = True

        result = Clipboard._xsel("test text")

        assert result is True
        mock_run.assert_called_once_with(["xsel", "--clipboard", "--input"], "test text")

    @patch("src.utils.SubprocessUtils.run_command_quiet")
    def test_tmux_buffer_method(self, mock_run):
        """Test _tmux_buffer calls correct command."""
        mock_run.return_value = True

        result = Clipboard._tmux_buffer("test text")

        assert result is True
        mock_run.assert_called_once_with(["tmux", "set-buffer", "--", "test text"])
