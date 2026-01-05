# Debugging Guide

This document explains how to enable and use the debugging features in tmux-flash-copy to troubleshoot issues.

## Table of Contents

- [Enabling/Disabling Debug Mode](#enablingdisabling-debug-mode)
  - [Enable Debug Mode](#enable-debug-mode)
  - [Disable Debug Mode](#disable-debug-mode)
- [Debug Log Location](#debug-log-location)
- [Visual Debug Indicator](#visual-debug-indicator)
- [What Gets Logged](#what-gets-logged)
  - [1. Session Header](#1-session-header)
  - [2. Configuration Settings](#2-configuration-settings)
  - [3. Tmux Environment](#3-tmux-environment)
  - [4. Pane Layout (ASCII Art)](#4-pane-layout-ascii-art)
  - [5. Search Activity](#5-search-activity)
  - [6. User Actions](#6-user-actions)
- [Common Issues and What to Look For](#common-issues-and-what-to-look-for)
  - [Issue: Clipboard Not Working](#issue-clipboard-not-working)
  - [Issue: No Matches Found](#issue-no-matches-found)
  - [Issue: Popup Not Appearing or Mispositioned](#issue-popup-not-appearing-or-mispositioned)
  - [Issue: Labels Not Appearing](#issue-labels-not-appearing)
  - [Issue: Performance Problems](#issue-performance-problems)
- [Reporting Issues](#reporting-issues)

## Enabling/Disabling Debug Mode

### Enable Debug Mode

Add the following to your `~/.tmux.conf`:

```bash
# Enable debug logging
set -g @flash-copy-debug "on"
```

After adding this, reload your tmux configuration:

```bash
tmux source ~/.tmux.conf
```

Or restart tmux entirely.

### Disable Debug Mode

```bash
# Disable debug logging
set -g @flash-copy-debug "off"
```

Then reload:

```bash
tmux source ~/.tmux.conf
```

Or restart tmux entirely.

## Debug Log Location

- **Path**: `~/.tmux-flash-copy-debug.log`
- **Max size**: 5 MB per file
- **Rotation**: Keeps 2 backup files (`.log`, `.log.1`, `.log.2`)
- **Total storage**: ~15 MB maximum

The log automatically rotates when it reaches 5MB, ensuring it doesn't consume excessive disk space.

- `~/.tmux-flash-copy-debug.log` - Current log
- `~/.tmux-flash-copy-debug.log.1` - Previous log (after rotation)
- `~/.tmux-flash-copy-debug.log.2` - Older log (after second rotation)

## Visual Debug Indicator

When debug mode is active, you'll see a persistent indicator on the right side of the search prompt:

```text
───────────────────────────────────────────────────
> search...                          !! DEBUG ON !!
```

This serves as a visual reminder that debug logging is enabled.

## What Gets Logged

The debug log captures information about each tmux-flash-copy session:

### 1. Session Header

```text
[2026-01-05T10:30:45.123] ================================================================================
[2026-01-05T10:30:45.123]   TMUX-FLASH-COPY DEBUG SESSION STARTED
[2026-01-05T10:30:45.123] ================================================================================
[2026-01-05T10:30:45.124] Python: 3.14.2 (final) (/usr/local/bin/python3)
[2026-01-05T10:30:45.125] Tmux: tmux 3.6a
[2026-01-05T10:30:45.125] Pane ID: %0
[2026-01-05T10:30:45.125] Log file: /Users/username/.tmux-flash-copy-debug.log
```

### 2. Configuration Settings

```text
[2026-01-05T10:30:45.126] ================================================================================
[2026-01-05T10:30:45.126]   Configuration Settings
[2026-01-05T10:30:45.126] ================================================================================
[2026-01-05T10:30:45.126] ui_mode: popup
[2026-01-05T10:30:45.126] auto_paste: False
[2026-01-05T10:30:45.126] reverse_search: True
[2026-01-05T10:30:45.126] case_sensitive: False
[2026-01-05T10:30:45.126] word_separators: ' -_.,;:!?/\()[]{}
<>~!@#$%^&*|+=[]{}?\'"'
[2026-01-05T10:30:45.126] prompt_placeholder_text: search...
[2026-01-05T10:30:45.126] highlight_colour: \033[1;33m
[2026-01-05T10:30:45.126] label_colour: \033[1;32m
[2026-01-05T10:30:45.126] prompt_position: bottom
[2026-01-05T10:30:45.126] prompt_indicator: >
[2026-01-05T10:30:45.126] prompt_colour: \033[1m
[2026-01-05T10:30:45.126] prompt_separator_colour: \033[38;5;242m
```

### 3. Tmux Environment

```text
[2026-01-05T10:30:45.130] ================================================================================
[2026-01-05T10:30:45.130]   Tmux Environment
[2026-01-05T10:30:45.130] ================================================================================
[2026-01-05T10:30:45.131] Sessions (1):
[2026-01-05T10:30:45.131]   - main (5 windows) ← ACTIVE
[2026-01-05T10:30:45.132] Windows (3):
[2026-01-05T10:30:45.132]   - [0] zsh (1 panes)
[2026-01-05T10:30:45.133]   - [1] vim (2 panes) ← ACTIVE
[2026-01-05T10:30:45.134] Panes (2):
[2026-01-05T10:30:45.134]   - %0: 80x24 (vim) ← ACTIVE
[2026-01-05T10:30:45.135]   - %1: 80x24 (zsh)
```

### 4. Pane Layout (ASCII Art)

```text
[2026-01-05T10:30:45.136] ================================================================================
[2026-01-05T10:30:45.136]   Pane Layout (ASCII)
[2026-01-05T10:30:45.136] ================================================================================
[2026-01-05T10:30:45.137] ┌────────────────────────────────┬───────────────────────────────┐
[2026-01-05T10:30:45.137] │                                │                               │
[2026-01-05T10:30:45.137] │        %0 80x24                │        %1 80x24               │
[2026-01-05T10:30:45.137] │                                │                               │
[2026-01-05T10:30:45.137] └────────────────────────────────┴───────────────────────────────┘
```

### 5. Search Activity

```text
[2026-01-05T10:30:47.456] Search query: 'test' -> 12 matches
[2026-01-05T10:30:47.457]   [a] line 5, col 10: 'testing'
[2026-01-05T10:30:47.457]   [s] line 8, col 23: 'test'
[2026-01-05T10:30:47.457]   [d] line 10, col 5: 'tests'
[2026-01-05T10:30:47.458]   [f] line 12, col 15: 'test-case'
[2026-01-05T10:30:47.458]   ... (first 10 matches shown)
```

### 6. User Actions

```text
[2026-01-05T10:30:49.123] User selected label 'a': 'testing'
[2026-01-05T10:30:49.125] Clipboard: Success via tmux OSC52
```

## Common Issues and What to Look For

### Issue: Clipboard Not Working

**What to check**:

```bash
grep -i clipboard ~/.tmux-flash-copy-debug.log | tail -5
```

**Expected output**:

- `Clipboard: Success via tmux OSC52` (best case)
- `Clipboard: Success via pbcopy (macOS)` (macOS fallback)
- `Clipboard: Success via xclip (Linux)` (Linux fallback)
- `Clipboard: Success via tmux buffer (tmux-only)` (last resort)

**Problem indicators**:

- `Clipboard: Failed - not in tmux` - tmux environment not detected
- No clipboard messages at all - clipboard code may not be running

**Solution**: See [CLIPBOARD.md](CLIPBOARD.md) for detailed troubleshooting.

### Issue: No Matches Found

**What to check**:

```bash
grep "Search query" ~/.tmux-flash-copy-debug.log | tail -5
```

**Expected output**:

```text
Search query: 'test' -> 12 matches
```

**Problem indicators**:

- `Search query: 'test' -> 0 matches` - no words matched your search

**Possible causes**:

- Search query doesn't match any visible text
- Word separators configuration doesn't match your content
- Case-sensitive search enabled when it should be off

**Solution**:

1. Check `word_separators` in the configuration section of the log
2. Try adjusting `@flash-copy-word-separators` in your `~/.tmux.conf`
3. Toggle `@flash-copy-case-sensitive` setting

### Issue: Popup Not Appearing or Mispositioned

**What to check**:

```bash
grep -A 20 "Pane Layout" ~/.tmux-flash-copy-debug.log | tail -25
```

Look for pane dimensions and positions.

**Problem indicators**:

- Incorrect pane dimensions
- Unusual pane positions

**Solution**:

1. Try `@flash-copy-ui-mode "window"` instead of popup
2. Check tmux version: `tmux -V` (should be 3.2+)
3. Verify pane dimensions match your expectations

### Issue: Labels Not Appearing

**What to check**:

```bash
grep "Search query" ~/.tmux-flash-copy-debug.log | tail -20
```

**Expected output**:

```text
[a] line 5, col 10: 'testing'
[s] line 8, col 23: 'test'
```

**Problem indicators**:

- No labels in brackets: `[ ] line 5, col 10: 'testing'`
- Very few labels when many matches exist

**Possible causes**:

- Label characters exhausted (too many matches)
- Label characters conflict with search query or matched words

**Solution**:

1. Refine your search query to reduce matches
2. Customize label characters in `src/search_interface.py`

### Issue: Performance Problems

**What to check**:
Look at timestamps between actions:

```bash
grep "\[" ~/.tmux-flash-copy-debug.log | tail -20
```

**Problem indicators**:

- Large time gaps between search updates
- Slow response to user input

**Possible causes**:

- Very large pane content
- Complex word separator patterns
- Many matches

**Solution**:

1. Use more specific search queries
2. Simplify word separators if customized
3. Consider using `@flash-copy-ui-mode "window"` instead of popup

## Reporting Issues

[Report issues via GitHub](https://github.com/Kristijan/tmux-flash-copy/issues)
