"""Tests for PopupUI module."""

import subprocess
from unittest.mock import MagicMock, patch

from src.clipboard import Clipboard
from src.config import FlashCopyConfig
from src.popup_ui import PopupUI
from src.search_interface import SearchInterface


class TestPopupUIAutoPaste:
    """Test auto-paste argument passing in PopupUI."""

    @patch("src.popup_ui.subprocess.run")
    @patch("src.popup_ui.TmuxPaneUtils.get_pane_dimensions")
    @patch("src.popup_ui.TmuxPaneUtils.calculate_popup_position")
    @patch("src.popup_ui.DebugLogger.get_instance")
    def test_popup_ui_passes_auto_paste_enabled_argument(
        self, mock_get_instance, mock_calc_pos, mock_get_dims, mock_subprocess
    ):
        """Test that PopupUI passes --auto-paste true when auto_paste_enable is True."""
        # Setup mocks
        mock_logger = MagicMock()
        mock_logger.log_file = ""
        mock_get_instance.return_value = mock_logger

        mock_get_dims.return_value = {
            "pane_x": 0,
            "pane_y": 0,
            "pane_width": 100,
            "pane_height": 20,
            "terminal_width": 200,
            "terminal_height": 50,
        }

        mock_calc_pos.return_value = {
            "x": 0,
            "y": 0,
            "width": 100,
            "height": 20,
        }

        # Mock subprocess.run to handle different commands
        def subprocess_side_effect(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0
            if "show-buffer" in cmd:
                result.stdout = "test result"
            else:
                result.stdout = ""
            return result

        mock_subprocess.side_effect = subprocess_side_effect

        # Create config with auto_paste_enable=True
        config = FlashCopyConfig(auto_paste_enable=True)

        # Create PopupUI
        clipboard = MagicMock(spec=Clipboard)
        search_interface = MagicMock(spec=SearchInterface)
        search_interface.reverse_search = True
        search_interface.word_separators = ""
        search_interface.case_sensitive = False
        popup_ui = PopupUI(
            pane_content="test content",
            search_interface=search_interface,
            clipboard=clipboard,
            pane_id="test_pane",
            config=config,
        )

        popup_ui._launch_popup()

        # Verify subprocess.run was called
        assert mock_subprocess.called
        # Get the first call (the popup command, not show-buffer or delete-buffer)
        call_args = mock_subprocess.call_args_list[0][0][0]

        # Check that --auto-paste true is in the arguments
        assert "--auto-paste" in call_args
        auto_paste_index = call_args.index("--auto-paste")
        assert call_args[auto_paste_index + 1] == "true"

    @patch("src.popup_ui.subprocess.run")
    @patch("src.popup_ui.TmuxPaneUtils.get_pane_dimensions")
    @patch("src.popup_ui.TmuxPaneUtils.calculate_popup_position")
    @patch("src.popup_ui.DebugLogger.get_instance")
    def test_popup_ui_passes_auto_paste_disabled_argument(
        self, mock_get_instance, mock_calc_pos, mock_get_dims, mock_subprocess
    ):
        """Test that PopupUI passes --auto-paste false when auto_paste_enable is False."""
        # Setup mocks
        mock_logger = MagicMock()
        mock_logger.log_file = ""
        mock_get_instance.return_value = mock_logger

        mock_get_dims.return_value = {
            "pane_x": 0,
            "pane_y": 0,
            "pane_width": 100,
            "pane_height": 20,
            "terminal_width": 200,
            "terminal_height": 50,
        }

        mock_calc_pos.return_value = {
            "x": 0,
            "y": 0,
            "width": 100,
            "height": 20,
        }

        # Mock subprocess.run to handle different commands
        def subprocess_side_effect(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0
            if "show-buffer" in cmd:
                result.stdout = "test result"
            else:
                result.stdout = ""
            return result

        mock_subprocess.side_effect = subprocess_side_effect

        # Create config with auto_paste_enable=False
        config = FlashCopyConfig(auto_paste_enable=False)

        # Create PopupUI
        clipboard = MagicMock(spec=Clipboard)
        search_interface = MagicMock(spec=SearchInterface)
        search_interface.reverse_search = True
        search_interface.word_separators = ""
        search_interface.case_sensitive = False
        popup_ui = PopupUI(
            pane_content="test content",
            search_interface=search_interface,
            clipboard=clipboard,
            pane_id="test_pane",
            config=config,
        )

        popup_ui._launch_popup()

        # Verify subprocess.run was called
        assert mock_subprocess.called
        # Get the first call (the popup command, not show-buffer or delete-buffer)
        call_args = mock_subprocess.call_args_list[0][0][0]

        # Check that --auto-paste false is in the arguments
        assert "--auto-paste" in call_args
        auto_paste_index = call_args.index("--auto-paste")
        assert call_args[auto_paste_index + 1] == "false"


class TestPopupUIErrorHandling:
    """Test error handling paths in PopupUI."""

    @patch("src.popup_ui.subprocess.run")
    @patch("src.popup_ui.TmuxPaneUtils.get_pane_dimensions")
    @patch("src.popup_ui.DebugLogger.get_instance")
    def test_popup_dimensions_fallback_on_none(
        self, mock_get_instance, mock_get_dims, mock_subprocess
    ):
        """Test fallback to tmux window dimensions when pane dimensions unavailable."""
        mock_logger = MagicMock()
        mock_logger.log_file = ""
        mock_get_instance.return_value = mock_logger

        # Return None to trigger fallback
        mock_get_dims.return_value = None

        # Mock subprocess.run to handle different commands
        def subprocess_side_effect(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0
            if "display-message" in cmd:
                result.stdout = "200,50"
            elif "show-buffer" in cmd:
                result.stdout = "test result"
            else:
                result.stdout = ""
            return result

        mock_subprocess.side_effect = subprocess_side_effect

        config = FlashCopyConfig()
        clipboard = MagicMock(spec=Clipboard)
        search_interface = MagicMock(spec=SearchInterface)
        search_interface.reverse_search = True
        search_interface.word_separators = ""
        search_interface.case_sensitive = False

        popup_ui = PopupUI(
            pane_content="test content",
            search_interface=search_interface,
            clipboard=clipboard,
            pane_id="test_pane",
            config=config,
        )

        popup_ui._launch_popup()

        # Verify subprocess was called for tmux query
        assert mock_subprocess.called
        first_call = mock_subprocess.call_args_list[0][0][0]
        assert "display-message" in first_call

    @patch("src.popup_ui.subprocess.run")
    @patch("src.popup_ui.TmuxPaneUtils.get_pane_dimensions")
    @patch("src.popup_ui.DebugLogger.get_instance")
    def test_popup_dimensions_fallback_on_subprocess_error(
        self, mock_get_instance, mock_get_dims, mock_subprocess
    ):
        """Test fallback to hardcoded dimensions on subprocess error."""
        mock_logger = MagicMock()
        mock_logger.log_file = ""
        mock_get_instance.return_value = mock_logger

        mock_get_dims.return_value = None

        # Mock subprocess to raise error on first call (display-message), succeed on others
        call_count = [0]

        def subprocess_side_effect(cmd, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1 and "display-message" in cmd:
                raise subprocess.CalledProcessError(1, "tmux")
            result = MagicMock()
            result.returncode = 0
            if "show-buffer" in cmd:
                result.stdout = "test result"
            else:
                result.stdout = ""
            return result

        mock_subprocess.side_effect = subprocess_side_effect

        config = FlashCopyConfig()
        clipboard = MagicMock(spec=Clipboard)
        search_interface = MagicMock(spec=SearchInterface)
        search_interface.reverse_search = True
        search_interface.word_separators = ""
        search_interface.case_sensitive = False

        popup_ui = PopupUI(
            pane_content="test content",
            search_interface=search_interface,
            clipboard=clipboard,
            pane_id="test_pane",
            config=config,
        )

        popup_ui._launch_popup()

        # Should still call popup command with fallback dimensions
        assert mock_subprocess.call_count >= 1
