# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

tmux-flash-copy is a tmux plugin inspired by flash.nvim that enables searching visible words in the current tmux pane and copying them to the clipboard using keyboard label shortcuts. The project is written in Python 3.9+ and integrates with tmux's OSC52 clipboard support.

## Development Commands

### Setup

```bash
# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate

# Install the project
uv sync --locked --all-extras --dev
```

### Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_clipboard.py

# Run specific test
uv run pytest tests/test_clipboard.py::TestClipboard::test_copy_success_with_osc52 -v
```

### Code Quality

```bash
# Type checking
uv run ty check

# Linting
uv run ruff check

# Formatting check
uv run ruff format --check

# Auto-fix linting issues
uv run ruff check --fix

# Auto-format code
uv run ruff format
```

### CI Checks Locally

```bash
# Run all CI checks in order
uv run ty check
uv run ruff check
uv run ruff format --check
uv run pytest --cov=src --cov-report=term-missing
```

## Architecture

### Entry Points

- `bin/tmux-flash-copy.py` - Main entry point called by tmux plugin loader, sets up UI mode (popup/window)
- `bin/tmux-flash-copy-interactive.py` - Interactive search interface that handles user input and rendering

### Core Modules (src/)

- `search_interface.py` - Core search logic matching words against queries, label generation (similar to flash.nvim algorithm)
- `config.py` - Reads tmux configuration options via `tmux show-option`
- `clipboard.py` - OSC52-based clipboard copying with fallbacks to pbcopy/xclip
- `pane_capture.py` - Captures pane content using `tmux capture-pane`
- `popup_ui.py` - Manages tmux popup/window UI lifecycle
- `ansi_utils.py` - ANSI escape sequence handling for colored output
- `debug_logger.py` - Debug logging system (enabled via `@flash-copy-debug`)
- `utils.py` - Subprocess utilities and tmux command wrappers

### Key Design Patterns

- Configuration is loaded from tmux options (`@flash-copy-*` variables)
- Word boundaries use tmux's `word-separators` option by default, overrideable via `@flash-copy-word-separators`
- Labels are assigned to matches in order determined by `@flash-copy-reverse-search` (bottom-to-top or top-to-bottom)
- Search is dynamic - updates as user types, with real-time label reassignment
- Clipboard operations use OSC52 (tmux 3.2+) as primary method, falling back to system tools

### tmux Integration

- Plugin is loaded via `tmux-flash-copy.tmux` (bash script)
- Communicates with tmux via subprocess calls to `tmux` CLI
- Uses tmux popup (overlay) or window modes for UI
- Binds to configurable key (default: `<prefix> S-f`)

### Label Assignment Algorithm

- Labels from `DEFAULT_LABELS = "asdfghjklqwertyuiopzxcvbnmASDFGHJKLQWERTYUIOPZXCVBNM"` are assigned to matches ensuring no label character appears as continuation of the search pattern (prevents accidental multi-character input).
- When creating labels in the interface, never add characters that will cause the pane contents to move or line wrap.
- Replace the next character when highlighting a match, so 'hello world' becomes 'hQllo world' ('Q', the label, replacing the letter 'e')
- When a whole word is matched, and the next character is a space, place the label in that spot, so 'hello world' becomes 'helloQworld' (replacing the space with the letter 'Q', being the label)

### Word separators

Word separators should only apply to the text that is copied to the clipboard, and not when searching.

As an example.
String: tmux bind-key "${bind_key}" run-shell "${PLUGIN_DIR}/bin/tmux-flash-copy.py"
Configured word separators: ' ()":,;<>~!@#$%^&*|+=[]{}?`''

I should be able to search for ${b and it apply a label to "${bind_key}". If that label is selected, only the word bind_key should be copied.

## Testing Philosophy

Tests use pytest with comprehensive coverage. Key testing patterns:

- Mock subprocess calls to tmux commands
- Mock clipboard operations (OSC52, pbcopy, xclip)
- Test both happy paths and error conditions
- Coverage target is maintained above 90%
- CI runs tests on Python 3.9, 3.10, 3.11, 3.12, 3.13, and 3.14

## Configuration System

All configuration is read from tmux options. When working with config:

- User-facing options use `@flash-copy-*` prefix
- Boolean options accept "on"/"off" or "true"/"false"
- Colors use ANSI escape sequences (e.g., `\033[1;33m`)
- Config is loaded once at plugin invocation (not cached between runs)

## Line Length and Formatting

Project uses ruff with:

- Line length: 100 characters
- Python 3.9+ target
- Import sorting via isort
- Multiple linting rules enabled (see pyproject.toml)
