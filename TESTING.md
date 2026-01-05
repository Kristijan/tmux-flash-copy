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
  - [Test Organization](#test-organization)
- [Continuous Integration (CI)](#continuous-integration-ci)
  - [GitHub Actions Workflow](#github-actions-workflow)
  - [Running CI Checks Locally](#running-ci-checks-locally)
  - [Test Timeouts](#test-timeouts)
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
uv pip install -e ".[dev]"
```

This installs:

- The `tmux-flash-copy` package in editable mode
- Test dependencies: `pytest`, `pytest-cov`
- All other development tools

### 5. Verify Installation

```bash
# Check that pytest is available
pytest --version

# Check Python can import the package
python -c "from src.clipboard import Clipboard; print('Success!')"
```

## Running Tests

### Run All Tests

```bash
pytest
```

**Output**:

```text
============================= test session starts ==============================
...
152 passed in 3.32s
```

Shows each test name as it runs.

### Run Tests with Coverage Report

```bash
# Terminal report
pytest --cov=src --cov-report=term-missing
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
pytest tests/test_clipboard.py
```

### Run Specific Test Classes

```bash
# Run all tests in TestClipboard class
pytest tests/test_clipboard.py::TestClipboard -v
```

### Run Specific Test Functions

```bash
# Run a single test
pytest tests/test_clipboard.py::TestClipboard::test_copy_success_with_osc52 -v

# Run multiple specific tests
pytest tests/test_clipboard.py::TestClipboard::test_copy_success_with_osc52 \
       tests/test_clipboard.py::TestClipboard::test_copy_fallback_to_pbcopy_on_macos -v
```

## Code Quality Checks

The following tools are used to ensure code quality:

### 1. Type Checking with `ty`

```bash
uvx ty check
```

### 2. Linting with `ruff`

```bash
uvx ruff check
```

### 3. Formatting with `ruff`

```bash
uvx ruff format --check
```

## Test Structure

### Test Organization

```text
tests/
├── __init__.py                 # Package marker
├── conftest.py                 # Shared fixtures
├── test_ansi_utils.py          # ANSI utilities
├── test_clipboard.py           # Clipboard operations
├── test_config.py              # Configuration loading
├── test_pane_capture.py        # Pane capture
├── test_search_interface.py    # Search & labeling
└── test_utils.py               # Utility functions
```

## Continuous Integration (CI)

### GitHub Actions Workflow

Tests run automatically on every pull request to `main`

### Running CI Checks Locally

Simulate CI environment locally:

```bash
# Create a fresh virtual environment
rm -rf .venv
uv venv
source .venv/bin/activate

# Install dependencies
uv pip install -e ".[dev]"

# Run all CI checks
uvx ty check
uvx ruff check --output-format=github
uvx ruff format --check
pytest --cov=src --cov-report=term-missing --cov-report=xml

# If all pass, your PR is ready!
```

### Test Timeouts

Some tests use subprocess timeouts:

```python
# Increase timeout if needed
result = SubprocessUtils.run_command(
    ["sleep", "10"],
    default="timeout",
    timeout=5  # Increase this value
)
```

## Related Documentation

- **pytest**: [https://docs.pytest.org/](https://docs.pytest.org/)
- **ruff**: [https://docs.astral.sh/ruff/](https://docs.astral.sh/ruff/)
- **ty**: [https://docs.astral.sh/ty/](https://docs.astral.sh/ty/)
- **uv**: [https://docs.astral.sh/uv](https://docs.astral.sh/uv)
