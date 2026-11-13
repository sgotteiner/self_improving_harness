---
name: bash-heredoc-backticks
description: "Never put markdown, backticks or ${} inside a Bash heredoc on this machine; write a script file and run it"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f81ed061-6004-4294-ae85-c1abb2f7f9c2
  modified: 2026-10-11T21:50:04.485Z
---

On this machine the Bash tool mangles heredocs: backticks get executed as command
substitution, `${...}` gets expanded, and the whole payload is re-quoted. Writing
markdown or code containing backticks through `python - <<'PY'` fails every time,
even with a quoted delimiter.

**Why:** the wrapper re-evaluates the command string, so the quoting that would
normally protect a heredoc does not survive.

**How to apply:** when the content has backticks, `${}`, or is markdown/code, use
the Write tool to put the script in the scratchpad and run it with
`python <path>`. Edit/Write for file content, Bash only for the invocation.
Happened five times (2026-09-22, 2026-09-22, 2026-10-02, 2026-10-12 twice): both times on
2026-10-12 it was a python heredoc editing the methodology/diary with `file.py` names in it.
Check before every Bash call: does the command text contain a backtick anywhere? Then it is
not a Bash call: use Edit/Write.
