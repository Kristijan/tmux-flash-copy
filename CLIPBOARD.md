# Clipboard Implementation

This document explains how tmux-flash-copy handles clipboard operations across different platforms and terminal configurations.

## Table of Contents

- [Overview](#overview)
- [Clipboard Methods (Priority Order)](#clipboard-methods-priority-order)
- [Internal: IPC buffer](#internal-ipc-buffer)
  - [1. OSC52 via tmux (Primary Method)](#1-osc52-via-tmux-primary-method)
  - [2. Native System Clipboard Tools (Fallback)](#2-native-system-clipboard-tools-fallback)
  - [3. tmux Buffer (Last Resort)](#3-tmux-buffer-last-resort)
- [Troubleshooting](#troubleshooting)
  - [OSC52 Not Working](#osc52-not-working)
  - [Native Tools Not Working](#native-tools-not-working)
  - [SSH/Remote Sessions](#sshremote-sessions)
- [Testing Clipboard](#testing-clipboard)
- [Related Documentation](#related-documentation)

## Overview

tmux-flash-copy uses a tiered fallback approach to ensure clipboard functionality works in as many environments as possible. The plugin attempts multiple methods in priority order, stopping at the first successful one.

## Clipboard Methods (Priority Order)

### 1. OSC52 via tmux (Primary Method)

**Command**: `tmux set-buffer -w`

**How it works**:

- Leverages tmux 3.2+'s built-in OSC52 support
- tmux sends an OSC52 escape sequence to the terminal
- The terminal intercepts the sequence and copies to system clipboard
- No external tools required

**Requirements**:

- tmux 3.2 or newer
- Terminal with OSC52 support (Ghostty, Kitty, Alacritty, etc...)

**Benefits**:

- Works over SSH
- No external dependencies
- Works in nested tmux sessions

**Limitations**:

- Requires terminal OSC52 support
- Some terminals need OSC52 explicitly enabled in their config

### 2. Native System Clipboard Tools (Fallback)

When OSC52 fails, the plugin falls back to platform-specific clipboard utilities.

#### macOS: `pbcopy`

**Command**: `pbcopy`

**How it works**:

- Reads from stdin and copies to system clipboard
- Always available on macOS

**Requirements**:

- macOS (any version)

**Benefits**:

- Pre-installed, no setup needed

**Limitations**:

- Doesn't work over SSH (local only)

#### Linux: `xclip` (Primary)

**Command**: `xclip -selection clipboard`

**How it works**:

- Copies to X11 clipboard selection
- Most common Linux clipboard tool

**Requirements**:

- X11 display server
- `xclip` package installed

**Limitations**:

- Requires X11
- Doesn't work over SSH without X11 forwarding
- Must be installed separately

#### Linux: `xsel` (Secondary Fallback)

**Command**: `xsel --clipboard --input`

**How it works**:

- Functionally similar to xclip
- Used if xclip is not available

**Requirements**:

- X11 display server
- `xsel` package installed

### 3. tmux Buffer (Last Resort)

**Command**: `tmux set-buffer`

**How it works**:

- Stores text in tmux's internal buffer
- Can be pasted within tmux using `tmux paste-buffer`
- Does NOT copy to system clipboard

**Requirements**:

- Just tmux (always available)

**Benefits**:

- No external dependencies
- Useful for tmux-only workflows

**Limitations**:

- Text only available within tmux
- Cannot paste into other applications
- Does not persist across tmux sessions

## Internal: IPC buffer

### The `__tmux_flash_copy_result__%X__` buffer

The plugin uses a special tmux buffer named `__tmux_flash_copy_result__%X__` (`%X` is the calling pane_id) for internal communication between the parent process and the interactive popup UI.

**Purpose**: Inter-process communication (IPC)

**How it works**:

- When the user selects text in the popup, the selection is stored in this named buffer
- The parent process reads from this buffer after the popup closes
- The buffer is immediately deleted after reading
- The text is then copied to the system clipboard using one of the methods above

**Key points**:

- This buffer is **separate** from clipboard operations
- It's used only for passing data from the popup to the parent process
- It exists only briefly (written → read → deleted)
- The double underscores (`__`) indicate this is an internal/private buffer
- Users will never interact with this buffer directly

**Why a tmux buffer for IPC?**

The plugin runs the interactive UI inside a `tmux display-popup`, which creates a pseudo-terminal. Standard output from the popup process cannot be captured by the parent, so we use a tmux buffer as a temporary storage mechanism.

After the text is read from the IPC buffer, it's copied to the system clipboard using the standard clipboard methods described above (OSC52, pbcopy, xclip, etc.).

## Troubleshooting

### OSC52 Not Working

**Check tmux version**:

```bash
tmux -V
# Should be 3.2 or newer
```

**Check terminal OSC52 support**:

Some terminals require OSC52 to be enabled in their configuration. Check your respective terminal documentation.

**Test OSC52 manually**:

```bash
# This should copy "test" to your clipboard
printf "\033]52;c;$(printf 'test' | base64)\007"
```

### Native Tools Not Working

**Check if tools are installed**:

```bash
# macOS
which pbcopy

# Linux
which xclip
which xsel
```

### SSH/Remote Sessions

**Best option**: Use OSC52

- Works transparently over SSH
- No X11 forwarding needed
- Terminal handles clipboard on local machine

**Alternative**: X11 Forwarding

```bash
# SSH with X11 forwarding
ssh -X user@remote-host

# Verify DISPLAY is set
echo $DISPLAY
```

## Testing Clipboard

To verify clipboard is working:

1. Enable debug mode

   ```bash
   # In ~/.tmux.conf
   set -g @flash-copy-debug "on"
   ```

2. Reload tmux config

   ```bash
   tmux source ~/.tmux.conf
   ```

3. Use tmux-flash-copy and check the debug log

   ```bash
   tail -f ~/.tmux-flash-copy-debug.log
   ```

Look for lines like:

- `Clipboard: Success via tmux OSC52`
- `Clipboard: Success via pbcopy (macOS)`
- `Clipboard: Success via xclip (Linux)`
- `Clipboard: Success via xsel (Linux)`
- `Clipboard: Success via tmux buffer (tmux-only)`

## Related Documentation

- [tmux clipboard integration](https://github.com/tmux/tmux/wiki/Clipboard)
- See [DEBUGGING.md](DEBUGGING.md) for troubleshooting clipboard issues
