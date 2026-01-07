# https://github.com/charmbracelet/vhs

# GIF output file
Output tmux-flash-copy-demo.gif

# Terminal setup
Set Theme "Catppuccin Mocha"
Set FontFamily "MonaspiceAr Nerd Font Mono"
Set FontSize 16
Set Padding 0
Set Framerate 60
Set Width 1000
Set Height 610

# Shell setup
Set Shell zsh

# Require programs
Require tmux
Require bat

# Launch tmux (hidden in GIF)
Hide
Type "tmux new -s tmux-flash-copy -n demo" Enter
Sleep 5s
Type "cd /Users/kristijan/GitHub/tmux-flash-copy" Enter
Type "clear" Enter
Show

# cat tmux-flash-copy.tmux file
Sleep 2s
Type "bat -pp tmux-flash-copy.tmux" Enter
Sleep 500ms

# Commentary
Type `"I'll now search for the word 'option_override' in this output using tmux-flash-copy"`
Sleep 2s
Ctrl+u

# Start tmux-flash-copy
Ctrl+p
Sleep 500ms
Type "f"
Sleep 500ms

# Type search query
Type@500ms "option"
Sleep 1.5s
Type "j"

# Paste copied text
Type `"I selected label 'j', and the text is now in my clipboard!"`
Sleep 1s
Ctrl+u
Copy "option_override"
Type "Pasting"
Type@500ms "..."
Type " "
Paste

# Admire the output for a bit.
Sleep 5s

# Kill the tmux server (hidden in GIF)
Hide
Type "tmux kill-session -t tmux-flash-copy" Enter