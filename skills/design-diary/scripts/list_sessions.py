"""List Claude Code session transcripts for a project, oldest first.

Usage:
    python list_sessions.py <transcript-dir>

<transcript-dir> is typically ~/.claude/projects/<project-slug>/ — the folder of
*.jsonl session files for the project you're building a diary for.
"""
import glob
import json
import os
import sys

DIR = sys.argv[1] if len(sys.argv) > 1 else "."

rows = []
for path in glob.glob(os.path.join(DIR, "*.jsonl")):
    first_ts = None
    first_user = None
    n_user = 0
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                ts = o.get("timestamp")
                if ts and first_ts is None:
                    first_ts = ts
                if o.get("type") == "user":
                    c = o.get("message", {}).get("content")
                    text = ""
                    if isinstance(c, str):
                        text = c
                    elif isinstance(c, list):
                        text = " ".join(b.get("text", "") for b in c
                                        if isinstance(b, dict) and b.get("type") == "text")
                    text = " ".join(text.split())
                    if text and not text.startswith("<"):
                        n_user += 1
                        if first_user is None:
                            first_user = text
    except Exception as e:
        first_user = f"(read error {e})"
    rows.append((first_ts or "0000", os.path.basename(path), n_user, (first_user or "")[:90]))

rows.sort(key=lambda r: r[0])
for i, (ts, name, nu, fu) in enumerate(rows, 1):
    day = ts[:16].replace("T", " ")
    print(f"{i:2}. {day}  u={nu:<3} {name[:8]}  {fu}")
print(f"\ntotal sessions: {len(rows)}")
