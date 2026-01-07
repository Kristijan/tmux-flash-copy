import importlib.util
from pathlib import Path

from src.ansi_utils import AnsiUtils
from src.config import FlashCopyConfig


def load_interactive_ui():
    script_path = Path(__file__).resolve().parents[1] / "bin" / "tmux-flash-copy-interactive.py"
    spec = importlib.util.spec_from_file_location("interactive_ui", str(script_path))
    # spec may be None according to the type checker; guard so mypy/ty know it's present
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module spec for {script_path}")

    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    loader = spec.loader
    # loader is typed as Optional[Loader]; we asserted it's not None above
    assert loader is not None
    loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod.InteractiveUI


def test_partial_match_replaces_next_character():
    """Searching for a partial match should replace the next character inside the word.

    Example: 'hello world' searching for 'h' => 'h<label>llo world'
    """
    interactive_cls = load_interactive_ui()

    pane_content = "hello world\n"
    config = FlashCopyConfig()
    ui = interactive_cls("pane", "/tmp", pane_content, {}, config)

    # Run search for single character 'h'
    matches = ui.search_interface.search("h")
    assert matches, "Expected at least one match"
    match = matches[0]
    label = match.label
    assert label, "Expected a label assigned to the match"

    line = pane_content.rstrip("\n").split("\n")[0]
    dimmed = ui._dim_coloured_line(line) if ui.search_query else line

    # Call the internal rendering helper
    rendered = ui._display_line_with_matches(dimmed, 0, line)

    visible = AnsiUtils.strip_ansi_codes(rendered)

    expected = "h" + label + "llo world"
    assert visible == expected


def test_whole_word_match_replaces_following_space():
    """When a whole word is matched and followed by a space, the space is replaced.

    Example: 'hello world' searching for 'hello' => 'hello<label>world'
    """
    interactive_cls = load_interactive_ui()

    pane_content = "hello world\n"
    config = FlashCopyConfig()
    ui = interactive_cls("pane", "/tmp", pane_content, {}, config)

    matches = ui.search_interface.search("hello")
    assert matches, "Expected at least one match"
    match = matches[0]
    label = match.label
    assert label, "Expected a label assigned to the match"

    line = pane_content.rstrip("\n").split("\n")[0]
    dimmed = ui._dim_coloured_line(line) if ui.search_query else line

    rendered = ui._display_line_with_matches(dimmed, 0, line)
    visible = AnsiUtils.strip_ansi_codes(rendered)

    expected = "hello" + label + "world"
    assert visible == expected
