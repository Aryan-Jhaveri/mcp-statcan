# statcan CLI: search -> metadata -> download, as a person would use it.
Output assets/cli-explore.gif
Source assets/tapes/_setup.tape

Type "statcan search 'consumer price index monthly' -n 4"
Enter
Wait@90s /^\$\s*$/
Sleep 4s
Ctrl+L

Type "statcan metadata 18-10-0004-01 | head -20"
Enter
Wait@90s /^\$\s*$/
Sleep 4s
Ctrl+L

Type "statcan download 18-10-0004-01 --key '2.2' --last 6 --format table"
Enter
Wait@90s /^\$\s*$/
Sleep 4s
