"""Dump one Claude Code session's user+assistant prose to a readable text file.

Keeps code fences and prose (code in a chat is cheap to read and often clarifies a
decision); drops thinking, tool calls, and tool results — the last is where logs and
other voluminous, low-signal output live.

Usage:
    python dump_chat.py <transcript-dir> <session-id-prefix>

Writes chat_<session-id-prefix>.txt into the current working directory.
"""
import glob
import json
import os
import sys

DIR = sys.argv[1]
sid = sys.argv[2]
matches = glob.glob(os.path.join(DIR, sid + "*.jsonl"))
if not matches:
    sys.exit(f"no session file matching {sid!r} in {DIR}")
path = matches[0]

out = []
first_ts = last_ts = None
for line in open(path, encoding="utf-8"):
    try:
        o = json.loads(line)
    except Exception:
        continue
    typ = o.get("type")
    if typ not in ("user", "assistant"):
        continue
    ts = o.get("timestamp", "")
    c = o.get("message", {}).get("content")
    text = ""
    if isinstance(c, str):
        text = c
    elif isinstance(c, list):
        # keep only authored text blocks (skip thinking / tool_use / tool_result)
        parts = [b.get("text", "") for b in c
                 if isinstance(b, dict) and b.get("type") == "text"]
        text = "\n".join(parts)
    text = (text or "").strip()
    # drop tool-result-only user turns and headless "conversation so far" echoes
    if not text or text.startswith("<") or "=== CONVERSATION SO FAR ===" in text:
        continue
    if first_ts is None:
        first_ts = ts
    last_ts = ts
    who = "USER" if typ == "user" else "ASSISTANT"
    out.append(f"[{who} @ {ts[:16]}]\n{text}\n")

body = "\n".join(out)
outpath = os.path.join(os.getcwd(), f"chat_{sid}.txt")
open(outpath, "w", encoding="utf-8").write(body)
print(f"session {sid}: {first_ts} .. {last_ts}")
print(f"turns kept: {len(out)}, chars: {len(body)}, written: {outpath}")
