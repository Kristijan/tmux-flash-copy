"""
Configuration loader module for reading tmux settings.

Provides a centralized way to read and parse tmux configuration options
with consistent error handling and type conversion.
"""

import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass
class FlashCopyConfig:
    """Configuration for tmux-flash-copy plugin."""

    reverse_search: bool = True
    case_sensitive: bool = False
    word_separators: Optional[str] = None
    prompt_placeholder_text: str = "search..."
    highlight_colour: str = "\033[1;33m"
    label_colour: str = "\033[1;32m"
    prompt_position: str = "bottom"
    prompt_indicator: str = ">"
    prompt_colour: str = "\033[1m"
    debug_enabled: bool = False
    auto_paste_enable: bool = True
    label_characters: Optional[str] = None
    idle_timeout: int = 15
    idle_warning: int = 5


class ConfigLoader:
    """Handles reading and parsing tmux configuration options."""

    @staticmethod
    def _read_tmux_option(option_name: str, default: str = "") -> str:
        """
        Read a tmux global option value.

        Args:
            option_name: The tmux option name (e.g., "@flash-copy-auto-paste")
            default: Default value if option doesn't exist or reading fails

        Returns:
            The option value as a string, or default if not found
        """
        try:
            result = subprocess.run(
                ["tmux", "show-option", "-gv", option_name],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return default
        except (subprocess.SubprocessError, OSError):
            return default

    @staticmethod
    def _read_tmux_window_option(option_name: str, default: str = "") -> str:
        """
        Read a tmux window option value.

        Args:
            option_name: The tmux option name (e.g., "word-separators")
            default: Default value if option doesn't exist or reading fails

        Returns:
            The option value as a string, or default if not found
        """
        try:
            result = subprocess.run(
                ["tmux", "show-window-option", "-g", option_name],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return default
        except (subprocess.SubprocessError, OSError):
            return default

    @staticmethod
    def parse_bool(value: str) -> bool:
        """
        Parse a string value as a boolean.

        Args:
            value: String value to parse

        Returns:
            True if value is one of: "on", "true", "1", "yes" (case-insensitive)
        """
        return value.lower() in ("on", "true", "1", "yes")

    @staticmethod
    def parse_choice(value: str, choices: list[str]) -> Optional[str]:
        """
        Parse and validate a choice from a list of allowed values.

        Args:
            value: String value to validate
            choices: List of allowed values (case-insensitive comparison)

        Returns:
            The matched choice in its original case, or None if not found
        """
        value_lower = value.lower()
        for choice in choices:
            if choice.lower() == value_lower:
                return choice
        return None

    @staticmethod
    def get_bool(option_name: str, default: bool = False) -> bool:
        """
        Get a boolean configuration option.

        Args:
            option_name: The tmux option name
            default: Default value if option doesn't exist

        Returns:
            Boolean value of the option
        """
        value = ConfigLoader._read_tmux_option(option_name, "")
        if not value:
            return default
        return ConfigLoader.parse_bool(value)

    @staticmethod
    def get_string(option_name: str, default: str = "") -> str:
        """
        Get a string configuration option.

        Args:
            option_name: The tmux option name
            default: Default value if option doesn't exist

        Returns:
            String value of the option
        """
        return ConfigLoader._read_tmux_option(option_name, default)

    @staticmethod
    def get_choice(option_name: str, choices: list[str], default: str = "") -> str:
        """
        Get a choice configuration option with validation.

        Args:
            option_name: The tmux option name
            choices: List of allowed values
            default: Default value if option doesn't exist or is invalid

        Returns:
            One of the provided choices, or default if invalid/missing
        """
        value = ConfigLoader._read_tmux_option(option_name, "")
        if not value:
            return default
        result = ConfigLoader.parse_choice(value, choices)
        return result if result else default

    @staticmethod
    def get_int(option_name: str, default: int = 0) -> int:
        """
        Get an integer configuration option.

        Args:
            option_name: The tmux option name
            default: Default value if option doesn't exist or is invalid

        Returns:
            Integer value of the option, or default if invalid/missing
        """
        value = ConfigLoader._read_tmux_option(option_name, "")
        if not value:
            return default
        try:
            return int(value)
        except ValueError:
            return default

    @staticmethod
    def get_word_separators(default: Optional[str] = None) -> Optional[str]:
        """
        Get word separators setting, with priority order.

        Priority:
        1. @flash-copy-word-separators (custom user override)
        2. word-separators window option (tmux built-in)

        The word-separators window option value comes as a quoted string and needs
        special handling to properly decode escape sequences.

        Args:
            default: Default value if option doesn't exist

        Returns:
            The word separators string, or default (None for use default pattern)
        """
        # First check for custom override
        custom_separators = ConfigLoader._read_tmux_option("@flash-copy-word-separators", "")
        if custom_separators:
            return custom_separators

        # Fallback to tmux's built-in word-separators window option
        output = ConfigLoader._read_tmux_window_option("word-separators", "")

        if not output or '"' not in output:
            return default

        try:
            # Output format: word-separators "value"
            # Extract the quoted value
            start = output.find('"')
            end = output.rfind('"')

            if start != -1 and end != -1 and start < end:
                # Get the quoted string and decode escape sequences
                quoted_value = output[start : end + 1]
                try:
                    # Use ast.literal_eval to properly decode the quoted string
                    import ast

                    return ast.literal_eval(quoted_value)
                except (ValueError, SyntaxError):
                    # Fallback: just extract between quotes without decoding
                    return output[start + 1 : end]
        except Exception:
            pass

        return default

    @staticmethod
    def load_all_flash_copy_config() -> FlashCopyConfig:
        """
        Load all flash-copy related configuration at once.

        Useful for loading all config in one place and passing around.

        Returns:
            FlashCopyConfig dataclass with all flash-copy configuration options
        """
        return FlashCopyConfig(
            reverse_search=ConfigLoader.get_bool("@flash-copy-reverse-search", default=True),
            case_sensitive=ConfigLoader.get_bool("@flash-copy-case-sensitive", default=False),
            word_separators=ConfigLoader.get_word_separators(),
            prompt_placeholder_text=ConfigLoader.get_string(
                "@flash-copy-prompt-placeholder-text", default="search..."
            ),
            highlight_colour=ConfigLoader.get_string(
                "@flash-copy-highlight-colour", default="\033[1;33m"
            ),
            label_colour=ConfigLoader.get_string("@flash-copy-label-colour", default="\033[1;32m"),
            prompt_position=ConfigLoader.get_choice(
                "@flash-copy-prompt-position", choices=["top", "bottom"], default="bottom"
            ),
            prompt_indicator=ConfigLoader.get_string("@flash-copy-prompt-indicator", default=">"),
            prompt_colour=ConfigLoader.get_string("@flash-copy-prompt-colour", default="\033[1m"),
            debug_enabled=ConfigLoader.get_bool("@flash-copy-debug", default=False),
            auto_paste_enable=ConfigLoader.get_bool("@flash-copy-auto-paste", default=True),
            label_characters=(
                ConfigLoader.get_string("@flash-copy-label-characters", default="") or None
            ),
            idle_timeout=ConfigLoader.get_int("@flash-copy-idle-timeout", default=15),
            idle_warning=ConfigLoader.get_int("@flash-copy-idle-warning", default=5),
        )
