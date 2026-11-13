"""UserPromptSubmit hook: print up to 3 related past cases. Any error -> silent exit 0."""
import json, os, sys

THRESHOLD = 2.5  # chosen by eval_recall.py
MAX_CHARS = 1500
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def main():
    if os.environ.get("RECALL_HOOK") == "0":
        return
    if not json.load(open(os.path.join(ROOT, "slots.json"), encoding="utf-8")).get("recall-hook", {}).get("enabled"):
        return
    prompt = json.load(sys.stdin).get("prompt", "")
    if len(prompt.split()) < 3:
        return
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import index
    out = []
    for score, cid in index.search(prompt, 3):
        if score < THRESHOLD:
            continue
        date, sit, lesson, right = index.meta(cid)
        out.append(f"Related past case (cases/{cid}.md, {date}): situation: {sit} Lesson: {lesson} Right: {right}")
    text = "\n".join(out)
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS - 3] + "..."
    if text:
        print(text)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
