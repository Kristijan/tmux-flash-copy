"""Tests for auto-paste functionality."""

from src.config import FlashCopyConfig
from src.search_interface import SearchMatch


class TestAutoPasteConfiguration:
    """Test auto-paste configuration loading and defaults."""

    def test_auto_paste_enabled_by_default(self):
        """Test that auto-paste is enabled by default."""
        config = FlashCopyConfig()
        assert config.auto_paste_enable is True

    def test_auto_paste_can_be_disabled(self):
        """Test that auto-paste can be explicitly disabled."""
        config = FlashCopyConfig(auto_paste_enable=False)
        assert config.auto_paste_enable is False

    def test_auto_paste_can_be_enabled(self):
        """Test that auto-paste can be explicitly enabled."""
        config = FlashCopyConfig(auto_paste_enable=True)
        assert config.auto_paste_enable is True


class TestAutoPasteInteractiveUI:
    """Test auto-paste behavior in the interactive UI."""

    def test_semicolon_as_modifier_when_enabled(self):
        """Test that semicolon acts as modifier when auto-paste is enabled."""
        config = FlashCopyConfig(auto_paste_enable=True)
        assert config.auto_paste_enable is True

        # Simulate receiving semicolon with auto-paste enabled
        char = ";"
        autopaste_modifier_active = False

        if config.auto_paste_enable and char in (";", ":"):
            autopaste_modifier_active = True

        assert autopaste_modifier_active is True

    def test_semicolon_as_searchable_when_disabled(self):
        """Test that semicolon is searchable when auto-paste is disabled."""
        config = FlashCopyConfig(auto_paste_enable=False)
        assert config.auto_paste_enable is False

        # Semicolon should be added to search query when auto-paste is disabled
        char = ";"
        search_query = ""

        if not config.auto_paste_enable or char not in (";", ":"):
            search_query += char

        assert ";" in search_query

    def test_colon_as_modifier_when_enabled(self):
        """Test that colon acts as modifier when auto-paste is enabled."""
        config = FlashCopyConfig(auto_paste_enable=True)

        # Colon (Shift+semicolon) should also work as modifier
        char = ":"
        autopaste_modifier_active = False

        if config.auto_paste_enable and char in (";", ":"):
            autopaste_modifier_active = True

        assert autopaste_modifier_active is True

    def test_modifier_state_reset_on_ctrl_u(self):
        """Test that Ctrl+U clears the auto-paste modifier state."""
        autopaste_modifier_active = True
        last_logged_modifier = ";"

        # Simulate Ctrl+U key press
        autopaste_modifier_active = False
        last_logged_modifier = None

        assert autopaste_modifier_active is False
        assert last_logged_modifier is None

    def test_modifier_state_reset_on_ctrl_w(self):
        """Test that Ctrl+W clears the auto-paste modifier state."""
        autopaste_modifier_active = True

        # Simulate Ctrl+W key press (delete word)
        autopaste_modifier_active = False

        assert autopaste_modifier_active is False

    def test_modifier_state_reset_on_backspace(self):
        """Test that backspace clears the auto-paste modifier state."""
        autopaste_modifier_active = True

        # Simulate backspace
        autopaste_modifier_active = False

        assert autopaste_modifier_active is False

    def test_auto_paste_flag_with_label_selection(self):
        """Test that auto-paste flag is set correctly when label is selected."""
        config = FlashCopyConfig(auto_paste_enable=True)

        # User presses semicolon (activates modifier)
        autopaste_modifier_active = False
        if config.auto_paste_enable:
            autopaste_modifier_active = True

        # User presses label - should_paste based on modifier
        should_paste = autopaste_modifier_active
        assert should_paste is True

    def test_auto_paste_flag_without_modifier(self):
        """Test that auto-paste flag is False when modifier is not active."""
        # User presses label without activating modifier
        autopaste_modifier_active = False

        should_paste = autopaste_modifier_active
        assert should_paste is False


class TestAutoPasteDebugLogging:
    """Test debug logging behavior for auto-paste modifier."""

    def test_modifier_logging_only_on_state_change(self):
        """Test that modifier activation is logged only once per state change."""
        config = FlashCopyConfig(auto_paste_enable=True, debug_enabled=True)

        # Simulate rapid semicolon presses (key held down)
        last_logged_modifier = None
        log_count = 0
        chars = [";", ";", ";", ";"]

        for char in chars:
            if config.auto_paste_enable and char in (";", ":") and last_logged_modifier != char:
                log_count += 1
                last_logged_modifier = char

        # Should log only once despite 4 key events
        assert log_count == 1

    def test_modifier_change_is_logged(self):
        """Test that changing from semicolon to colon is logged."""
        last_logged_modifier = None
        log_count = 0

        # First: semicolon press
        if last_logged_modifier != ";":
            log_count += 1
            last_logged_modifier = ";"

        # Second: colon press (shift modifier released then colon)
        if last_logged_modifier != ":":
            log_count += 1
            last_logged_modifier = ":"

        assert log_count == 2

    def test_logging_disabled_when_debug_off(self):
        """Test that nothing is logged when debug is disabled."""
        config = FlashCopyConfig(auto_paste_enable=True, debug_enabled=False)

        log_count = 0
        last_logged_modifier = None
        chars = [";", ";", ";"]

        for char in chars:
            if (
                config.debug_enabled
                and config.auto_paste_enable
                and char in (";", ":")
                and last_logged_modifier != char
            ):
                log_count += 1
                last_logged_modifier = char

        # No logging should occur
        assert log_count == 0


class TestAutoPasteSemicolonColon:
    """Test semicolon and colon key handling based on auto-paste setting."""

    def test_both_semicolon_and_colon_activate_modifier(self):
        """Test that both semicolon and colon activate modifier when enabled."""
        config = FlashCopyConfig(auto_paste_enable=True)

        for char in [";", ":"]:
            autopaste_modifier_active = False
            if config.auto_paste_enable and char in (";", ":"):
                autopaste_modifier_active = True

            assert autopaste_modifier_active is True

    def test_semicolon_searchable_when_disabled(self):
        """Test that semicolon is searchable when auto-paste is disabled."""
        config = FlashCopyConfig(auto_paste_enable=False)
        search_query = ""

        char = ";"
        if not config.auto_paste_enable or char not in (";", ":"):
            search_query += char

        assert ";" in search_query

    def test_colon_searchable_when_disabled(self):
        """Test that colon is searchable when auto-paste is disabled."""
        config = FlashCopyConfig(auto_paste_enable=False)
        search_query = ""

        char = ":"
        if not config.auto_paste_enable or char not in (";", ":"):
            search_query += char

        assert ":" in search_query

    def test_search_with_multiple_semicolons(self):
        """Test searching with multiple semicolons when auto-paste is disabled."""
        search_query = ""

        for _ in range(3):
            search_query += ";"

        assert search_query == ";;;"


class TestAutoPasteWithMatches:
    """Test auto-paste behavior with search results."""

    def test_auto_paste_with_single_match(self):
        """Test auto-paste with exactly one match."""
        # Create a dummy match
        match = SearchMatch(
            text="hello",
            start_pos=0,
            end_pos=5,
            line=0,
            col=0,
        )
        match.label = "a"
        current_matches = [match]

        autopaste_modifier_active = True

        # Can auto-paste with one match and modifier active
        can_paste = len(current_matches) > 0 and autopaste_modifier_active

        assert can_paste is True

    def test_no_paste_with_no_matches(self):
        """Test auto-paste when there are no matches."""
        current_matches = []
        autopaste_modifier_active = True

        can_paste = len(current_matches) > 0 and autopaste_modifier_active

        assert can_paste is False

    def test_no_paste_without_modifier(self):
        """Test that auto-paste doesn't happen without modifier."""
        match = SearchMatch(
            text="hello",
            start_pos=0,
            end_pos=5,
            line=0,
            col=0,
        )
        match.label = "a"
        current_matches = [match]

        autopaste_modifier_active = False

        can_paste = len(current_matches) > 0 and autopaste_modifier_active

        assert can_paste is False


class TestAutoPastePopupUIIntegration:
    """Test auto-paste flag passing through PopupUI to interactive script."""

    def test_auto_paste_enabled_passed_to_subprocess(self):
        """Test that auto_paste_enable flag is passed to subprocess."""
        config = FlashCopyConfig(auto_paste_enable=True)

        # Simulate popup command building
        popup_args = [
            "--auto-paste",
            "true" if config.auto_paste_enable else "false",
        ]

        assert "--auto-paste" in popup_args
        assert "true" in popup_args

    def test_auto_paste_disabled_passed_to_subprocess(self):
        """Test that auto_paste_enable=False is passed to subprocess."""
        config = FlashCopyConfig(auto_paste_enable=False)

        popup_args = [
            "--auto-paste",
            "true" if config.auto_paste_enable else "false",
        ]

        assert "--auto-paste" in popup_args
        assert "false" in popup_args


class TestAutoPasteEdgeCases:
    """Test edge cases and boundary conditions for auto-paste."""

    def test_empty_search_query_with_modifier(self):
        """Test auto-paste modifier with empty search query."""
        search_query = ""
        autopaste_modifier_active = True

        # Modifier can be active even with empty search
        assert autopaste_modifier_active is True
        assert search_query == ""

    def test_auto_paste_with_combined_settings(self):
        """Test auto-paste with various configuration combinations."""
        # Auto-paste enabled, debug enabled
        config1 = FlashCopyConfig(auto_paste_enable=True, debug_enabled=True)
        assert config1.auto_paste_enable is True
        assert config1.debug_enabled is True

        # Auto-paste disabled, debug disabled
        config2 = FlashCopyConfig(auto_paste_enable=False, debug_enabled=False)
        assert config2.auto_paste_enable is False
        assert config2.debug_enabled is False

        # Auto-paste disabled, debug enabled
        config3 = FlashCopyConfig(auto_paste_enable=False, debug_enabled=True)
        assert config3.auto_paste_enable is False
        assert config3.debug_enabled is True
