"""Tests for config module."""

from unittest.mock import MagicMock, patch

from src.config import ConfigLoader, FlashCopyConfig


class TestFlashCopyConfig:
    """Test FlashCopyConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = FlashCopyConfig()
        assert config.auto_paste is False
        assert config.reverse_search is True
        assert config.case_sensitive is False
        assert config.word_separators is None
        assert config.prompt_placeholder_text == "search..."
        assert config.highlight_colour == "\033[1;33m"
        assert config.label_colour == "\033[1;32m"
        assert config.prompt_position == "bottom"
        assert config.prompt_indicator == ">"
        assert config.prompt_colour == "\033[1m"
        assert config.debug_enabled is False

    def test_custom_values(self):
        """Test configuration with custom values."""
        config = FlashCopyConfig(
            auto_paste=True,
            reverse_search=False,
            case_sensitive=True,
            word_separators=" -",
            prompt_placeholder_text="find...",
            highlight_colour="\033[1;31m",
            label_colour="\033[1;34m",
            prompt_position="top",
            prompt_indicator=">>",
            prompt_colour="\033[1;36m",
            debug_enabled=True,
        )
        assert config.auto_paste is True
        assert config.reverse_search is False
        assert config.case_sensitive is True
        assert config.word_separators == " -"
        assert config.prompt_placeholder_text == "find..."
        assert config.highlight_colour == "\033[1;31m"
        assert config.label_colour == "\033[1;34m"
        assert config.prompt_position == "top"
        assert config.prompt_indicator == ">>"
        assert config.prompt_colour == "\033[1;36m"
        assert config.debug_enabled is True


class TestConfigLoader:
    """Test ConfigLoader functionality."""

    @patch("subprocess.run")
    def test_read_tmux_option_success(self, mock_run):
        """Test reading tmux option successfully."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "test_value\n"
        mock_run.return_value = mock_result

        result = ConfigLoader._read_tmux_option("@test-option")

        assert result == "test_value"
        mock_run.assert_called_once_with(
            ["tmux", "show-option", "-gv", "@test-option"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )

    @patch("subprocess.run")
    def test_read_tmux_option_not_found(self, mock_run):
        """Test reading tmux option that doesn't exist."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        result = ConfigLoader._read_tmux_option("@missing-option", default="default_value")

        assert result == "default_value"

    @patch("subprocess.run")
    def test_read_tmux_option_timeout(self, mock_run):
        """Test reading tmux option with timeout."""
        mock_run.side_effect = TimeoutError("Timeout")

        result = ConfigLoader._read_tmux_option("@test-option", default="timeout_default")

        assert result == "timeout_default"

    @patch("subprocess.run")
    def test_read_tmux_option_subprocess_error(self, mock_run):
        """Test reading tmux option with subprocess error."""
        mock_run.side_effect = OSError("Subprocess error")

        result = ConfigLoader._read_tmux_option("@test-option", default="error_default")

        assert result == "error_default"

    @patch("subprocess.run")
    def test_read_tmux_window_option_success(self, mock_run):
        """Test reading tmux window option successfully."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = 'word-separators " -"\n'
        mock_run.return_value = mock_result

        result = ConfigLoader._read_tmux_window_option("word-separators")

        assert result == 'word-separators " -"'
        mock_run.assert_called_once_with(
            ["tmux", "show-window-option", "-g", "word-separators"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )

    @patch("subprocess.run")
    def test_read_tmux_window_option_not_found(self, mock_run):
        """Test reading tmux window option that doesn't exist."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        result = ConfigLoader._read_tmux_window_option("missing-option", default="default")

        assert result == "default"

    def test_parse_bool_true_variations(self):
        """Test parsing boolean true values."""
        assert ConfigLoader.parse_bool("on") is True
        assert ConfigLoader.parse_bool("ON") is True
        assert ConfigLoader.parse_bool("true") is True
        assert ConfigLoader.parse_bool("TRUE") is True
        assert ConfigLoader.parse_bool("1") is True
        assert ConfigLoader.parse_bool("yes") is True
        assert ConfigLoader.parse_bool("YES") is True

    def test_parse_bool_false_variations(self):
        """Test parsing boolean false values."""
        assert ConfigLoader.parse_bool("off") is False
        assert ConfigLoader.parse_bool("false") is False
        assert ConfigLoader.parse_bool("0") is False
        assert ConfigLoader.parse_bool("no") is False
        assert ConfigLoader.parse_bool("") is False
        assert ConfigLoader.parse_bool("random") is False

    def test_parse_choice_valid(self):
        """Test parsing valid choice."""
        choices = ["top", "bottom"]
        assert ConfigLoader.parse_choice("top", choices) == "top"
        assert ConfigLoader.parse_choice("bottom", choices) == "bottom"

    def test_parse_choice_case_insensitive(self):
        """Test parsing choice with case-insensitive matching."""
        choices = ["top", "bottom"]
        assert ConfigLoader.parse_choice("TOP", choices) == "top"
        assert ConfigLoader.parse_choice("Bottom", choices) == "bottom"

    def test_parse_choice_invalid(self):
        """Test parsing invalid choice."""
        choices = ["top", "bottom"]
        assert ConfigLoader.parse_choice("invalid", choices) is None
        assert ConfigLoader.parse_choice("", choices) is None

    @patch("src.config.ConfigLoader._read_tmux_option")
    def test_get_bool_true(self, mock_read):
        """Test getting boolean option with true value."""
        mock_read.return_value = "on"

        result = ConfigLoader.get_bool("@test-option")

        assert result is True
        mock_read.assert_called_once_with("@test-option", "")

    @patch("src.config.ConfigLoader._read_tmux_option")
    def test_get_bool_false(self, mock_read):
        """Test getting boolean option with false value."""
        mock_read.return_value = "off"

        result = ConfigLoader.get_bool("@test-option")

        assert result is False

    @patch("src.config.ConfigLoader._read_tmux_option")
    def test_get_bool_default(self, mock_read):
        """Test getting boolean option with default value."""
        mock_read.return_value = ""

        result = ConfigLoader.get_bool("@test-option", default=True)

        assert result is True

    @patch("src.config.ConfigLoader._read_tmux_option")
    def test_get_string_with_value(self, mock_read):
        """Test getting string option with value."""
        mock_read.return_value = "test_value"

        result = ConfigLoader.get_string("@test-option")

        assert result == "test_value"

    @patch("src.config.ConfigLoader._read_tmux_option")
    def test_get_string_default(self, mock_read):
        """Test getting string option with default value."""
        mock_read.return_value = ""

        result = ConfigLoader.get_string("@test-option", default="default_value")

        assert result == ""

    @patch("src.config.ConfigLoader._read_tmux_option")
    def test_get_choice_valid(self, mock_read):
        """Test getting choice option with valid value."""
        mock_read.return_value = "top"

        result = ConfigLoader.get_choice("@test-option", choices=["top", "bottom"])

        assert result == "top"

    @patch("src.config.ConfigLoader._read_tmux_option")
    def test_get_choice_invalid(self, mock_read):
        """Test getting choice option with invalid value."""
        mock_read.return_value = "invalid"

        result = ConfigLoader.get_choice("@test-option", choices=["top", "bottom"], default="top")

        assert result == "top"

    @patch("src.config.ConfigLoader._read_tmux_option")
    def test_get_choice_empty(self, mock_read):
        """Test getting choice option with empty value."""
        mock_read.return_value = ""

        result = ConfigLoader.get_choice(
            "@test-option", choices=["top", "bottom"], default="bottom"
        )

        assert result == "bottom"

    @patch("src.config.ConfigLoader._read_tmux_option")
    def test_get_word_separators_custom_override(self, mock_read):
        """Test getting word separators with custom override."""
        mock_read.return_value = " -_"

        result = ConfigLoader.get_word_separators()

        assert result == " -_"
        mock_read.assert_called_once_with("@flash-copy-word-separators", "")

    @patch("src.config.ConfigLoader._read_tmux_window_option")
    @patch("src.config.ConfigLoader._read_tmux_option")
    def test_get_word_separators_from_tmux(self, mock_read_option, mock_read_window):
        """Test getting word separators from tmux window option."""
        mock_read_option.return_value = ""  # No custom override
        mock_read_window.return_value = 'word-separators " -_@"'

        result = ConfigLoader.get_word_separators()

        assert result == " -_@"

    @patch("src.config.ConfigLoader._read_tmux_window_option")
    @patch("src.config.ConfigLoader._read_tmux_option")
    def test_get_word_separators_default(self, mock_read_option, mock_read_window):
        """Test getting word separators with default value."""
        mock_read_option.return_value = ""
        mock_read_window.return_value = ""

        result = ConfigLoader.get_word_separators(default="default_seps")

        assert result == "default_seps"

    @patch("src.config.ConfigLoader._read_tmux_window_option")
    @patch("src.config.ConfigLoader._read_tmux_option")
    def test_get_word_separators_no_quotes(self, mock_read_option, mock_read_window):
        """Test getting word separators when output has no quotes."""
        mock_read_option.return_value = ""
        mock_read_window.return_value = "word-separators"

        result = ConfigLoader.get_word_separators(default="default")

        assert result == "default"

    @patch("src.config.ConfigLoader._read_tmux_window_option")
    @patch("src.config.ConfigLoader._read_tmux_option")
    def test_get_word_separators_with_escape_sequences(self, mock_read_option, mock_read_window):
        """Test getting word separators with escape sequences."""
        mock_read_option.return_value = ""
        mock_read_window.return_value = 'word-separators " \\n\\t"'

        result = ConfigLoader.get_word_separators()

        assert result == " \n\t"

    @patch("src.config.ConfigLoader._read_tmux_window_option")
    @patch("src.config.ConfigLoader._read_tmux_option")
    def test_get_word_separators_malformed_quotes(self, mock_read_option, mock_read_window):
        """Test getting word separators with malformed quotes."""
        mock_read_option.return_value = ""
        mock_read_window.return_value = 'word-separators "'

        result = ConfigLoader.get_word_separators(default="default")

        assert result == "default"

    @patch("src.config.ConfigLoader.get_choice")
    @patch("src.config.ConfigLoader.get_bool")
    @patch("src.config.ConfigLoader.get_string")
    @patch("src.config.ConfigLoader.get_word_separators")
    def test_load_all_flash_copy_config(self, mock_word_sep, mock_string, mock_bool, mock_choice):
        """Test loading all flash-copy configuration."""
        mock_choice.side_effect = ["bottom"]
        mock_bool.side_effect = [False, True, False, False]
        mock_word_sep.return_value = None
        mock_string.side_effect = [
            "search...",
            "\033[1;33m",
            "\033[1;32m",
            ">",
            "\033[1m",
        ]

        config = ConfigLoader.load_all_flash_copy_config()

        assert isinstance(config, FlashCopyConfig)
        assert config.auto_paste is False
        assert config.reverse_search is True
        assert config.case_sensitive is False
        assert config.word_separators is None
        assert config.prompt_placeholder_text == "search..."
        assert config.highlight_colour == "\033[1;33m"
        assert config.label_colour == "\033[1;32m"
        assert config.prompt_position == "bottom"
        assert config.prompt_indicator == ">"
        assert config.prompt_colour == "\033[1m"
        assert config.debug_enabled is False
