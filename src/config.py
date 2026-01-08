"""
Configuration loader module for reading tmux settings.

Provides a centralized way to read and parse tmux configuration options
with consistent error handling and type conversion.
"""

import ast
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

    # Cache for batched option reads to reduce subprocess calls
    _global_options_cache: Optional[dict[str, str]] = None
    _window_options_cache: Optional[dict[str, str]] = None

    @staticmethod
    def _read_all_global_options() -> dict[str, str]:
        """
        Batch read all tmux global options in a single subprocess call.

        Returns:
            Dictionary mapping option names to their values
        """
        options = {}
        try:
            result = subprocess.run(
                ["tmux", "show-options", "-g"],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    # Parse lines like: @flash-copy-debug off
                    # or: @flash-copy-prompt-colour "\033[1m"
                    if " " in line:
                        parts = line.split(" ", 1)
                        if len(parts) == 2:
                            key = parts[0]
                            value = parts[1].strip()
                            # Remove surrounding quotes and decode escape sequences if present
                            if value.startswith('"') and value.endswith('"'):
                                try:
                                    # Use ast.literal_eval to properly decode escape sequences
                                    value = ast.literal_eval(value)
                                except (ValueError, SyntaxError):
                                    # Fallback: just strip quotes without decoding
                                    value = value[1:-1]
                            options[key] = value
        except (subprocess.SubprocessError, OSError):
            pass
        return options

    @staticmethod
    def _read_all_window_options() -> dict[str, str]:
        """
        Batch read all tmux window options in a single subprocess call.

        Returns:
            Dictionary mapping option names to their values
        """
        options = {}
        try:
            result = subprocess.run(
                ["tmux", "show-window-option", "-g"],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if " " in line:
                        parts = line.split(" ", 1)
                        if len(parts) == 2:
                            key = parts[0]
                            value = parts[1].strip()
                            # Remove surrounding quotes and decode escape sequences if present
                            if value.startswith('"') and value.endswith('"'):
                                try:
                                    # Use ast.literal_eval to properly decode escape sequences
                                    value = ast.literal_eval(value)
                                except (ValueError, SyntaxError):
                                    # Fallback: just strip quotes without decoding
                                    value = value[1:-1]
                            options[key] = value
        except (subprocess.SubprocessError, OSError):
            pass
        return options

    @staticmethod
    def _run_tmux_command(args: list[str], default: str = "") -> str:
        """
        Run a tmux command and return stdout or default on error.

        Args:
            args: List of command arguments to pass to subprocess.run
            default: Default value if command fails

        Returns:
            The command output as a string, or default if command fails
        """
        try:
            result = subprocess.run(
                args,
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
    def _read_tmux_option(option_name: str, default: str = "") -> str:
        """
        Read a tmux global option value.

        Uses cached values if available to reduce subprocess calls.

        Args:
            option_name: The tmux option name (e.g., "@flash-copy-auto-paste")
            default: Default value if option doesn't exist or reading fails

        Returns:
            The option value as a string, or default if not found
        """
        # Check cache first
        if ConfigLoader._global_options_cache is not None:
            return ConfigLoader._global_options_cache.get(option_name, default)

        # Fall back to individual read if cache not populated
        return ConfigLoader._run_tmux_command(
            ["tmux", "show-option", "-gv", option_name],
            default,
        )

    @staticmethod
    def _read_tmux_window_option(option_name: str, default: str = "") -> str:
        """
        Read a tmux window option value.

        Uses cached values if available to reduce subprocess calls.

        Args:
            option_name: The tmux option name (e.g., "word-separators")
            default: Default value if option doesn't exist or reading fails

        Returns:
            The option value as a string, or default if not found
        """
        # Check cache first
        if ConfigLoader._window_options_cache is not None:
            return ConfigLoader._window_options_cache.get(option_name, default)

        # Fall back to individual read if cache not populated
        return ConfigLoader._run_tmux_command(
            ["tmux", "show-window-option", "-g", option_name],
            default,
        )

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
    def get_optional_string(option_name: str) -> Optional[str]:
        """
        Get string option, returning None if empty or not set.

        Args:
            option_name: The tmux option name

        Returns:
            The option value as a string, or None if empty or not found
        """
        value = ConfigLoader.get_string(option_name, default="")
        return value if value else None

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

        if not output:
            return default

        # Check if this is the full command output format: "word-separators \"value\""
        if output.startswith("word-separators"):
            # Full format from direct command - extract the value part
            if len(output) == len("word-separators"):
                # Edge case: "word-separators" with no value
                return default
            elif output[len("word-separators")] == " ":
                # Has a space separator, extract value part
                output = output[len("word-separators ") :]
                if not output:
                    return default

        # Check if it's in quoted format "value" (from non-cached read)
        if output.startswith('"'):
            # Starts with quote - should be in quoted format
            if output.endswith('"') and len(output) > 1:
                try:
                    # Use ast.literal_eval to properly decode escape sequences
                    return ast.literal_eval(output)
                except (ValueError, SyntaxError):
                    # Fallback: just strip quotes without decoding
                    return output[1:-1]
            else:
                # Malformed quoted value (e.g., just '"' or doesn't end with quote)
                return default

        # Otherwise, it's already decoded (from cache)
        # Return it as-is if it's not empty, otherwise return default
        return output if output else default

    @staticmethod
    def load_all_flash_copy_config() -> FlashCopyConfig:
        """
        Load all flash-copy related configuration at once.

        Useful for loading all config in one place and passing around.

        Returns:
            FlashCopyConfig dataclass with all flash-copy configuration options
        """
        # Batch read all options in single subprocess calls for performance
        ConfigLoader._global_options_cache = ConfigLoader._read_all_global_options()
        ConfigLoader._window_options_cache = ConfigLoader._read_all_window_options()

        # word-separators doesn't appear in batch read, so read it individually
        # and add to cache for consistency
        if "word-separators" not in ConfigLoader._window_options_cache:
            # For word-separators, we need to preserve leading/trailing spaces
            # since they're significant separator characters
            try:
                result = subprocess.run(
                    ["tmux", "show-window-option", "-gv", "word-separators"],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=5,
                )
                if result.returncode == 0 and result.stdout:
                    # Only strip newlines, not spaces
                    word_sep_output = result.stdout.rstrip("\n\r")
                    ConfigLoader._window_options_cache["word-separators"] = word_sep_output
            except (subprocess.SubprocessError, OSError):
                pass

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
            label_characters=ConfigLoader.get_optional_string("@flash-copy-label-characters"),
            idle_timeout=ConfigLoader.get_int("@flash-copy-idle-timeout", default=15),
            idle_warning=ConfigLoader.get_int("@flash-copy-idle-warning", default=5),
        )
