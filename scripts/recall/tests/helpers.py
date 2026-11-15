"""Shared by the tests: build a transcript (jsonl) from a few entries, a temp git repo as a stand-in setup, brain stubs."""
import json, os, subprocess, sys, tempfile

RECALL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, RECALL)

_n = [0]


def user(text):
    return {"type": "user", "message": {"role": "user", "content": text}}


def tool(name, inp, id=None):
    _n[0] += 1
    return {"type": "tool_use", "id": id or f"toolu_{_n[0]}", "name": name, "input": inp}


def assistant(*blocks):
    return {"type": "assistant", "message": {"role": "assistant",
            "content": [{"type": "text", "text": b} if isinstance(b, str) else b for b in blocks]}}


def result(tool_id, text):
    return {"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": tool_id, "content": [{"type": "text", "text": text}]}]}}


def notice(task_id, tool_id, text="done"):
    return user(f"<task-notification>\n<task-id>{task_id}</task-id>\n<tool-use-id>{tool_id}</tool-use-id>\n"
                f"<status>completed</status>\n<result>{text}</result>\n</task-notification>")


def launch(kind, agent_id, tool_id, desc="work"):
    """The two entries of an Agent call started in the background."""
    return [assistant(tool("Agent", {"subagent_type": kind, "description": desc, "prompt": desc}, tool_id)),
            result(tool_id, f"Async agent launched successfully.\nagentId: {agent_id} (internal ID)")]


def resume(agent_id, tool_id=None):
    t = tool("SendMessage", {"to": agent_id, "summary": "more", "message": "continue"}, tool_id)
    return [assistant(t), result(t["id"], '{"success":true,"message":"Resuming agent"}')]


def transcript(entries, cwd=None):
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(dict(e, cwd=cwd) if cwd else e) + "\n")
    return path


def git_repo(files):
    """A temp git repo with `files` {rel: text} committed; returns its root."""
    root = tempfile.mkdtemp(prefix="setup-")
    g = lambda *a: subprocess.run(["git", "-C", root, *a], check=True, capture_output=True)
    g("init", "-q"), g("config", "user.email", "t@example.invalid"), g("config", "user.name", "t")
    for rel, text in files.items():
        p = os.path.join(root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w", encoding="utf-8").write(text)
    g("add", "."), g("commit", "-q", "-m", "first")
    return root


def brain_says(reply):
    """A stand-in for brain.ask returning `reply`; .prompts holds what it was asked."""
    def ask(prompt, system="", tag=""):
        ask.prompts.append(prompt)
        return reply, 1
    ask.prompts = []
    return ask
