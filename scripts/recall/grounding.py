"""Is a text his own? Anything written down as his (a why, what he asked) must repeat a run of words from one of his
messages; the model's paraphrase is a guess and a guess written down becomes false record."""
import re

MIN_SPAN_WORDS = 4  # a text counts as grounded when it repeats this many consecutive words of his message
MIN_MESSAGE_WORDS = 3  # a shorter message ("yes", "ok do it") states no reason of its own and grounds nothing
MIN_CONTENT_WORDS = 2  # a span of filler ("it to work and that") is not his reason: it needs this many words that are not these
FILLER = set("a an the and or but so to of in on at for with from by as is are was were be been it its this that these those "
             "i you he she we they me my your his her our their do does did have has had not no yes can could would should will "
             "just also then than if when what which who how".split())


def common_span(text, message):
    """The longest run of at least MIN_SPAN_WORDS consecutive words of `message` that also occurs in `text`, quoted from
    `message` as he wrote it; '' when there is none or the message has fewer than MIN_MESSAGE_WORDS words."""
    mine = [(m.group(0).lower(), m.start(), m.end()) for m in re.finditer(r"\w+", message)]
    theirs = [m.group(0).lower() for m in re.finditer(r"\w+", text)]
    if len(mine) < MIN_MESSAGE_WORDS:
        return ""
    best, end, prev = 0, 0, [0] * (len(theirs) + 1)  # longest common substring over words
    for i, (w, _, _) in enumerate(mine):
        row = [0] * (len(theirs) + 1)
        for j, v in enumerate(theirs):
            if w == v:
                row[j + 1] = prev[j] + 1
                if row[j + 1] > best:
                    best, end = row[j + 1], i
        prev = row
    if best < MIN_SPAN_WORDS:
        return ""
    span = message[mine[end - best + 1][1]:mine[end][2]]
    content = [w for w in re.findall(r"\w+", span.lower()) if w not in FILLER]
    return span if len(content) >= MIN_CONTENT_WORDS else ""


def best_span(text, messages):
    """The longest common_span of `text` with any of `messages`."""
    return max((common_span(text, m) for m in messages), key=len, default="")
