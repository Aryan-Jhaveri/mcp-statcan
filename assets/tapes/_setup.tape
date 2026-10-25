# Shared setup: statcan from the project venv, plain prompt, scratch output dir.
# Run tapes from the repo root: vhs assets/tapes/cli-explore.tape
Set Shell "bash"
Set FontSize 15
Set Width 1200
Set Height 680
Set Padding 20
Set Theme "Builtin Solarized Light"
Set TypingSpeed 35ms
Set WindowBar Colorful

Hide
Type "export PATH=$PWD/.venv/bin:$PATH PS1='$ ' COLUMNS=110 && mkdir -p /tmp/statcan-demo && cd /tmp/statcan-demo && clear"
Enter
Show
