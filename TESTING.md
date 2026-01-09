# Testing Guide

This document explains how to set up your local development environment and run tests for tmux-flash-copy.

## Table of Contents

- [Prerequisites](#prerequisites)
  - [Required Tools](#required-tools)
- [Setting Up Development Environment](#setting-up-development-environment)
  - [1. Clone the Repository](#1-clone-the-repository)
  - [2. Create a Virtual Environment](#2-create-a-virtual-environment)
  - [3. Activate the Virtual Environment](#3-activate-the-virtual-environment)
  - [4. Install Dependencies](#4-install-dependencies)
  - [5. Verify Installation](#5-verify-installation)
- [Running Tests](#running-tests)
  - [Run All Tests](#run-all-tests)
  - [Run Tests with Coverage Report](#run-tests-with-coverage-report)
  - [Run Specific Test Files](#run-specific-test-files)
  - [Run Specific Test Classes](#run-specific-test-classes)
  - [Run Specific Test Functions](#run-specific-test-functions)
- [Code Quality Checks](#code-quality-checks)
  - [1. Type Checking with `ty`](#1-type-checking-with-ty)
  - [2. Linting with `ruff`](#2-linting-with-ruff)
  - [3. Formatting with `ruff`](#3-formatting-with-ruff)
- [Test Structure](#test-structure)
  - [Test Organisation](#test-organisation)
- [Continuous Integration (CI)](#continuous-integration-ci)
  - [GitHub Actions Workflow](#github-actions-workflow)
  - [Running CI Checks Locally](#running-ci-checks-locally)
- [Related Documentation](#related-documentation)

## Prerequisites

### Required Tools

1. **Python 3.9+**

   ```bash
   python3 --version
   # Should be 3.9 or higher
   ```

2. **uv**

    `uv` isn't explicitly required, but the development uses it to create virtual environments, and to perform checks us `ty` & `ruff`.

3. **Git**

   ```bash
   git --version
   ```

## Setting Up Development Environment

### 1. Clone the Repository

```bash
git clone https://github.com/kristijan/tmux-flash-copy.git
cd tmux-flash-copy
```

### 2. Create a Virtual Environment

```bash
# Create a new virtual environment
uv venv

# This creates a .venv directory in the project root
```

### 3. Activate the Virtual Environment

```bash
source .venv/bin/activate
```

### 4. Install Dependencies

Install dependencies:

```bash
uv sync --locked --all-extras --dev
```

This installs:

- The `tmux-flash-copy` package in editable mode
- Test dependencies:
  - `pytest-cov`
  - `pytest`
  - `ruff`
  - `ty`

### 5. Verify Installation

```bash
# Check that pytest is available
uv run pytest --version

# Check Python can import the package
python -c "from src.clipboard import Clipboard; print('Success!')"
```

## Running Tests

### Run All Tests

```bash
uv run ty check
uv run ruff check
uv run ruff format --check
uv run pytest
```

**Output**:

```text
============================= test session starts ==============================
...
235 passed in 3.79s
```

Shows each test name as it runs.

### Run Tests with Coverage Report

```bash
# Terminal report
uv run pytest --cov=src --cov-report=term-missing
```

The resulting HTML reports will be in a directory named `htmlcov/`

**Coverage Summary**:

```text
Name                      Stmts   Miss  Cover   Missing
-------------------------------------------------------
src/ansi_utils.py            40      1    98%   89
src/clipboard.py             66      5    92%   80, 84, 90, 94, 127
src/config.py                87      6    93%   84-85, 211-215
src/pane_capture.py          17      0   100%
src/search_interface.py     122      2    98%   90, 231
src/utils.py                 56      0   100%
-------------------------------------------------------
TOTAL                       673    299    56%
```

### Run Specific Test Files

```bash
# Run only clipboard tests
uv run pytest tests/test_clipboard.py
```

### Run Specific Test Classes

```bash
# Run all tests in TestClipboard class
uv run pytest tests/test_clipboard.py::TestClipboard -v
```

### Run Specific Test Functions

```bash
# Run a single test
uv run pytest tests/test_clipboard.py::TestClipboard::test_copy_success_with_osc52 -v

# Run multiple specific tests
uv run pytest tests/test_clipboard.py::TestClipboard::test_copy_success_with_osc52 \
              tests/test_clipboard.py::TestClipboard::test_copy_fallback_to_pbcopy_on_macos -v
```

## Code Quality Checks

The following tools are used to ensure code quality:

### 1. Type Checking with `ty`

```bash
uv run ty check
```

### 2. Linting with `ruff`

```bash
uv run ruff check
```

### 3. Formatting with `ruff`

```bash
uv run ruff format --check
```

## Test Structure

### Test Organisation

```text
tests/
├── __init__.py                 # Package marker
├── conftest.py                 # Shared fixtures
├── test_ansi_utils.py          # ANSI utilities (TestAnsiStyles, TestTerminalSequences, TestControlChars, TestAnsiUtils)
├── test_auto_paste.py          # Auto-paste functionality (TestAutoPasteConfiguration, TestAutoPasteInteractiveUI, TestAutoPasteDebugLogging, etc.)
├── test_clipboard.py           # Clipboard operations (TestClipboard)
├── test_config.py              # Configuration loading (TestFlashCopyConfig, TestConfigLoader)
├── test_debug_logger.py        # Debug logging functionality
├── test_idle_timeout.py        # Idle timeout behavior (TestIdleTimeoutWarning, TestIdleTimeoutExit, TestIdleTimeoutWarningValidation, etc.)
├── test_label_placement.py     # Label placement rendering logic
├── test_pane_capture.py        # Pane capture (TestPaneCapture)
├── test_popup_ui.py            # Popup UI functionality (TestPopupUIAutoPaste, TestPopupUIErrorHandling)
├── test_search_interface.py    # Search & labeling (TestSearchMatch, TestSearchInterface)
└── test_utils.py               # Utility functions (TestSubprocessUtils, TestPaneDimensions, TestTmuxPaneUtils)
```

### Test Files Overview

#### `test_ansi_utils.py`

Tests for ANSI escape sequence handling and utilities:

- **TestAnsiStyles**: ANSI style constants (BOLD, DIM, RESET)
- **TestTerminalSequences**: Terminal sequence constants (CLEAR_SCREEN)
- **TestControlChars**: Control character constants (CTRL_C, ESC, BACKSPACE, ENTER, etc.)
- **TestAnsiUtils**: Strip ANSI codes, visible length calculation, position mapping

#### `test_auto_paste.py`

Tests for auto-paste functionality that allows pasting selected text directly:

- **TestAutoPasteConfiguration**: Configuration defaults and settings
- **TestAutoPasteInteractiveUI**: Semicolon/colon modifier behavior
- **TestAutoPasteDebugLogging**: Debug logging for modifier state changes
- **TestAutoPasteSemicolonColon**: Semicolon and colon key handling
- **TestAutoPasteWithMatches**: Auto-paste with search results
- **TestAutoPastePopupUIIntegration**: Flag passing to subprocess
- **TestAutoPasteEdgeCases**: Edge cases and boundary conditions

#### `test_clipboard.py`

Tests for clipboard operations with OSC52 and fallback mechanisms:

- **TestClipboard**: OSC52 copying, pbcopy/xclip fallbacks, error handling

#### `test_config.py`

Tests for configuration loading from tmux options:

- **TestFlashCopyConfig**: Default values, color settings, boolean options
- **TestConfigLoader**: Loading from tmux options, parsing values

#### `test_debug_logger.py`

Tests for debug logging system (enabled via `@flash-copy-debug`).

#### `test_idle_timeout.py`

Tests for idle timeout functionality that auto-exits after inactivity:

- **TestIdleTimeoutWarning**: Warning display after threshold

- **TestIdleTimeoutExit**: Exit behavior after timeout
- **TestIdleTimeoutWarningValidation**: Warning validation logic
- **TestIdleTimeoutReset**: Timeout reset on user input
- **TestIdleTimeoutConstants**: Default timeout values
- **TestIdleTimeoutDebugLogging**: Debug logging for timeout events

#### `test_label_placement.py`

Tests for label placement rendering logic:

- Partial match label placement (replaces next character)
- Whole word match label placement (replaces following space)

#### `test_pane_capture.py`

Tests for capturing tmux pane content:

- **TestPaneCapture**: Pane content capture via `tmux capture-pane`

#### `test_popup_ui.py`

Tests for tmux popup/window UI management:

- **TestPopupUIAutoPaste**: Auto-paste flag handling in popup
- **TestPopupUIErrorHandling**: Error handling and cleanup

#### `test_search_interface.py`

Tests for search and label assignment logic:

- **TestSearchMatch**: Search match data structure
- **TestSearchInterface**: Word matching, label generation, dynamic search updates

#### `test_utils.py`

Tests for utility functions and tmux integration:

- **TestSubprocessUtils**: Subprocess command execution with timeouts
- **TestPaneDimensions**: Pane dimension parsing
- **TestTmuxPaneUtils**: Tmux pane information retrieval

## Continuous Integration (CI)

### GitHub Actions Workflow

Tests run automatically on every pull request to `main`.

**Workflow**: `.github/workflows/plugin-testing.yml`

**What it runs**:

1. Tests against Python 3.9, 3.10, 3.11, and 3.12
2. Type checking: `uv run ty check --output-format=github`
3. Linting: `uv run ruff check --output-format=github`
4. Formatting: `uv run ruff format --check`
5. Tests with coverage: `uv run pytest --cov=src --cov-report=term-missing --cov-report=xml`
6. Uploads coverage to Codecov (Python 3.12 only)

### Running CI Checks Locally

Simulate CI environment locally:

```bash
# Create a fresh virtual environment
rm -rf .venv
uv venv
source .venv/bin/activate

# Install the project
uv sync --locked --all-extras --dev

# Run all CI checks
uv run ty check
uv run ruff check
uv run ruff format
uv run pytest

# If all pass, your PR is ready!
```

## Related Documentation

- **pytest**: [https://docs.pytest.org/](https://docs.pytest.org/)
- **ruff**: [https://docs.astral.sh/ruff/](https://docs.astral.sh/ruff/)
- **ty**: [https://docs.astral.sh/ty/](https://docs.astral.sh/ty/)
- **uv**: [https://docs.astral.sh/uv](https://docs.astral.sh/uv)
