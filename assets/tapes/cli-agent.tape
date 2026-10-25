# statcan CLI in agent mode: JSON envelopes, file + summary, stable exit codes.
Output assets/cli-agent.gif
Source assets/tapes/_setup.tape

Type "# Download to a file; the envelope summarizes it, so the agent never reads the CSV"
Enter
Type "statcan --json download 18-10-0004-01 --key '2+3+5+6.2' --start 2020-01 -o cpi.csv | jq '{ok, rows, series_count, period_range, path}'"
Enter
Wait@90s /^\$\s*$/
Sleep 4s

Type "# Failures: JSON on stderr, typed exit code, and a hint for the next step"
Enter
Type `statcan --json metadata 99999999; echo "exit code: $?"`
Enter
Wait@90s /^\$\s*$/
Sleep 4s

Type "statcan describe | jq -c '.contract.exit_codes | to_entries[] | {code: .key, name: .value.name}'"
Enter
Wait@90s /^\$\s*$/
Sleep 4s
