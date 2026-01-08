"""Tests for config module."""

from unittest.mock import MagicMock, patch

from src.config import ConfigLoader, FlashCopyConfig


class TestFlashCopyConfig:
    """Test FlashCopyConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = FlashCopyConfig()
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
        assert config.auto_paste_enable is True

    def test_custom_values(self):
        """Test configuration with custom values."""
        config = FlashCopyConfig(
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
            auto_paste_enable=False,
        )
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
        assert config.auto_paste_enable is False


class TestConfigLoader:
    """Test ConfigLoader functionality."""

    @patch("subprocess.run")
    def test_read_all_global_options_success(self, mock_run):
        """Test batch reading all global options."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '@flash-copy-debug off\n@flash-copy-prompt-colour "\\033[1m"\n'
        mock_run.return_value = mock_result

        result = ConfigLoader._read_all_global_options()

        assert "@flash-copy-debug" in result
        assert result["@flash-copy-debug"] == "off"
        assert "@flash-copy-prompt-colour" in result
        assert result["@flash-copy-prompt-colour"] == "\033[1m"

    @patch("subprocess.run")
    def test_read_all_global_options_failure(self, mock_run):
        """Test batch reading global options with failure."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        result = ConfigLoader._read_all_global_options()

        assert result == {}

    @patch("subprocess.run")
    def test_read_all_global_options_subprocess_error(self, mock_run):
        """Test batch reading global options with subprocess error."""
        mock_run.side_effect = OSError("Subprocess failed")

        result = ConfigLoader._read_all_global_options()

        assert result == {}

    @patch("subprocess.run")
    def test_read_all_global_options_invalid_escape_fallback(self, mock_run):
        """Test batch reading with invalid escape sequence falls back to strip quotes."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        # Invalid escape sequence that can't be decoded by ast.literal_eval
        mock_result.stdout = r'@flash-copy-test "\x{invalid}"' + "\n"
        mock_run.return_value = mock_result

        result = ConfigLoader._read_all_global_options()

        # Should fall back to just stripping quotes
        assert "@flash-copy-test" in result
        assert result["@flash-copy-test"] == r"\x{invalid}"

    @patch("subprocess.run")
    def test_read_all_window_options_success(self, mock_run):
        """Test batch reading all window options."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = 'mode-keys vi\nword-separators " -"\n'
        mock_run.return_value = mock_result

        result = ConfigLoader._read_all_window_options()

        assert "mode-keys" in result
        assert result["mode-keys"] == "vi"
        assert "word-separators" in result
        assert result["word-separators"] == " -"

    @patch("subprocess.run")
    def test_read_all_window_options_failure(self, mock_run):
        """Test batch reading window options with failure."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        result = ConfigLoader._read_all_window_options()

        assert result == {}

    @patch("subprocess.run")
    def test_read_all_window_options_subprocess_error(self, mock_run):
        """Test batch reading window options with subprocess error."""
        mock_run.side_effect = OSError("Subprocess failed")

        result = ConfigLoader._read_all_window_options()

        assert result == {}

    @patch("subprocess.run")
    def test_read_all_window_options_invalid_escape_fallback(self, mock_run):
        """Test batch reading with invalid escape sequence falls back to strip quotes."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        # Invalid escape that can't be decoded by ast.literal_eval
        mock_result.stdout = r'test-option "\x{invalid}"' + "\n"
        mock_run.return_value = mock_result

        result = ConfigLoader._read_all_window_options()

        # Should fall back to just stripping quotes
        assert "test-option" in result
        assert result["test-option"] == r"\x{invalid}"

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
    def test_get_int_with_value(self, mock_read):
        """Test getting integer option with valid value."""
        mock_read.return_value = "30"

        result = ConfigLoader.get_int("@test-option", default=15)

        assert result == 30

    @patch("src.config.ConfigLoader._read_tmux_option")
    def test_get_int_default(self, mock_read):
        """Test getting integer option with missing value."""
        mock_read.return_value = ""

        result = ConfigLoader.get_int("@test-option", default=15)

        assert result == 15

    @patch("src.config.ConfigLoader._read_tmux_option")
    def test_get_int_invalid_value(self, mock_read):
        """Test getting integer option with invalid value."""
        mock_read.return_value = "not_a_number"

        result = ConfigLoader.get_int("@test-option", default=15)

        assert result == 15

    @patch("src.config.ConfigLoader._read_tmux_option")
    def test_get_int_negative(self, mock_read):
        """Test getting integer option with negative value."""
        mock_read.return_value = "-5"

        result = ConfigLoader.get_int("@test-option", default=15)

        assert result == -5

    def test_read_tmux_option_with_cache(self):
        """Test reading tmux option uses cache when available."""
        # Populate cache
        ConfigLoader._global_options_cache = {"@test-option": "cached_value"}

        result = ConfigLoader._read_tmux_option("@test-option", default="default")

        assert result == "cached_value"

        # Clean up
        ConfigLoader._global_options_cache = None

    def test_read_tmux_window_option_with_cache(self):
        """Test reading tmux window option uses cache when available."""
        # Populate cache
        ConfigLoader._window_options_cache = {"test-option": "cached_value"}

        result = ConfigLoader._read_tmux_window_option("test-option", default="default")

        assert result == "cached_value"

        # Clean up
        ConfigLoader._window_options_cache = None

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

    @patch("src.config.ConfigLoader._read_tmux_window_option")
    @patch("src.config.ConfigLoader._read_tmux_option")
    def test_get_word_separators_invalid_escape_sequence(self, mock_read_option, mock_read_window):
        """Test handling of invalid escape sequences in word-separators."""
        mock_read_option.return_value = ""
        # Invalid escape sequence that causes ast.literal_eval to fail
        mock_read_window.return_value = 'word-separators "\\x999"'

        result = ConfigLoader.get_word_separators()

        # Should fall back to extracting between quotes without decoding
        # The string is extracted as-is: \x999
        assert result == "\x999"

    @patch("src.config.ConfigLoader._read_tmux_window_option")
    @patch("src.config.ConfigLoader._read_tmux_option")
    def test_get_word_separators_syntax_error(self, mock_read_option, mock_read_window):
        """Test handling of syntax errors in word-separators."""
        mock_read_option.return_value = ""
        # Unclosed quote that causes SyntaxError
        mock_read_window.return_value = 'word-separators "invalid\\""'

        result = ConfigLoader.get_word_separators()

        # Should fall back to extracting between quotes
        # The backslash-quote becomes just a quote: invalid"
        assert result == 'invalid"'

    @patch("src.config.ConfigLoader._read_tmux_window_option")
    @patch("src.config.ConfigLoader._read_tmux_option")
    def test_get_word_separators_empty_after_prefix(self, mock_read_option, mock_read_window):
        """Test word-separators when value is empty after prefix."""
        mock_read_option.return_value = ""
        # Just the prefix with nothing after
        mock_read_window.return_value = "word-separators"

        result = ConfigLoader.get_word_separators(default="default_value")

        assert result == "default_value"

    @patch("src.config.ConfigLoader._read_tmux_window_option")
    @patch("src.config.ConfigLoader._read_tmux_option")
    def test_get_word_separators_space_only_after_prefix(self, mock_read_option, mock_read_window):
        """Test word-separators when only space after prefix."""
        mock_read_option.return_value = ""
        # Prefix with space but empty value
        mock_read_window.return_value = "word-separators "

        result = ConfigLoader.get_word_separators(default="default_value")

        assert result == "default_value"

    @patch("src.config.ConfigLoader._read_tmux_window_option")
    @patch("src.config.ConfigLoader._read_tmux_option")
    def test_get_word_separators_already_decoded(self, mock_read_option, mock_read_window):
        """Test word-separators when value is already decoded (from cache)."""
        mock_read_option.return_value = ""
        # Already decoded value (no quotes)
        mock_read_window.return_value = " -_"

        result = ConfigLoader.get_word_separators()

        assert result == " -_"

    @patch("subprocess.run")
    def test_load_all_flash_copy_config_word_sep_subprocess_error(self, mock_run):
        """Test load_all_flash_copy_config handles subprocess error when reading word-separators."""
        # First two calls succeed (global and window options)
        # Third call fails (word-separators individual read)
        mock_result_success = MagicMock()
        mock_result_success.returncode = 0
        mock_result_success.stdout = ""

        mock_run.side_effect = [
            mock_result_success,  # global options
            mock_result_success,  # window options
            OSError("Subprocess failed"),  # word-separators read
        ]

        # Should not raise, should use default
        config = ConfigLoader.load_all_flash_copy_config()

        assert config is not None

    @patch("src.config.ConfigLoader._read_all_window_options")
    @patch("src.config.ConfigLoader._read_all_global_options")
    @patch("src.config.ConfigLoader.get_int")
    @patch("src.config.ConfigLoader.get_choice")
    @patch("src.config.ConfigLoader.get_bool")
    @patch("src.config.ConfigLoader.get_string")
    @patch("src.config.ConfigLoader.get_word_separators")
    def test_load_all_flash_copy_config(
        self,
        mock_word_sep,
        mock_string,
        mock_bool,
        mock_choice,
        mock_int,
        mock_global_opts,
        mock_window_opts,
    ):
        """Test loading all flash-copy configuration."""
        mock_global_opts.return_value = {}
        mock_window_opts.return_value = {}
        mock_choice.side_effect = ["bottom"]
        mock_bool.side_effect = [True, False, False, True]  # auto_paste_enable defaults to True
        mock_word_sep.return_value = None
        mock_string.side_effect = [
            "search...",
            "\033[1;33m",
            "\033[1;32m",
            ">",
            "\033[1m",
            "",
        ]
        mock_int.side_effect = [15, 5]  # idle_timeout, idle_warning

        config = ConfigLoader.load_all_flash_copy_config()

        assert isinstance(config, FlashCopyConfig)
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
        assert config.auto_paste_enable is True
        assert config.idle_timeout == 15
        assert config.idle_warning == 5

    @patch("src.config.ConfigLoader._read_all_window_options")
    @patch("src.config.ConfigLoader._read_all_global_options")
    @patch("src.config.ConfigLoader.get_int")
    @patch("src.config.ConfigLoader.get_choice")
    @patch("src.config.ConfigLoader.get_bool")
    @patch("src.config.ConfigLoader.get_string")
    @patch("src.config.ConfigLoader.get_word_separators")
    def test_load_all_flash_copy_config_auto_paste_disabled(
        self,
        mock_word_sep,
        mock_string,
        mock_bool,
        mock_choice,
        mock_int,
        mock_global_opts,
        mock_window_opts,
    ):
        """Test loading flash-copy configuration with auto-paste disabled."""
        mock_global_opts.return_value = {}
        mock_window_opts.return_value = {}
        mock_choice.side_effect = ["top"]
        mock_bool.side_effect = [True, True, True, False]  # auto_paste_enable is False
        mock_word_sep.return_value = " -"
        mock_string.side_effect = [
            "search...",
            "\033[1;33m",
            "\033[1;32m",
            ">",
            "\033[1m",
            "",
        ]
        mock_int.side_effect = [30, 10]  # custom idle_timeout, idle_warning

        config = ConfigLoader.load_all_flash_copy_config()

        assert config.auto_paste_enable is False
        assert config.idle_timeout == 30
        assert config.idle_warning == 10
