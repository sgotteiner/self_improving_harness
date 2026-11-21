# Cases

One file per past mistake, `<slug>.md`. Search matches the request against `situation`; replay tests the setup.

- Frontmatter: `id`, `date` (when it happened), `source` (file where it is recorded).
- `situation`: 1-4 phrasings of how this shows up in a request (a lesson approved from a proposal starts with 1; aim for 2+ when writing one by hand). Search matches on these.
- `wrong` / `right`: what was done wrong, what to do instead. `lesson`: one sentence.
- `level`: `advice` (default; brought in when the situation repeats), `check` (verified at the output gate before finishing), `rule` (hard rule in code).
- `occurrences` (count) and `last_seen` (date): maintained by the hooks. Each real occurrence is a recall example of its case, stored in `cases/history/<id>.md` as one block: situation, what the assistant did, what he did not like (his words, in general wording), and the lesson it belongs to. The brain rewrites the raw words into this structure (no names, paths, people or session ids; an occurrence that still fails a privacy scan is not stored). The raw words and transcript path stay only in the local `scripts/recall/history.db`. Every block is embedded as its own document for the case, next to the case fields. Nothing is generated or made up: examples are real occurrences only.
- Captured drafts wait in `cases/_pending/` (`asked`, `his_words`) until the owner approves them. `python -I scripts/recall/capture.py approve <slug> <level>` is one self-checking step: moves the case here (drops `his_words`/`source`), rebuilds the index, cleans and publishes the occurrences, encodes the embeddings now, then checks that every required field and every part of every occurrence is present, privacy, and that the case ranks #1-2 when its lesson and two situation lines are searched. Any failed step exits non-zero. `capture.py check [slug]` runs the same checks over all cases.
- `replay`: a prompt that recreates the situation in a fresh session.
- `pass_if`: checkable signals for the replay (words that must or must not appear, a tool not used, a question asked).
- Public repo: no personal data, amounts, or company internals. Short but not missing: no size cap, every part present and non-empty.
