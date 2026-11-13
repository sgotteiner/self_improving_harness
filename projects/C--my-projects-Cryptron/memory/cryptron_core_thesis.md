---
name: cryptron-core-thesis
description: "Cryptron's real \"why\" — automate the fuel supply to reasoning (sensing/memory/processing), not the reasoning itself."
metadata: 
  node_type: memory
  type: project
  originSessionId: f4f688de-e613-47ee-b566-9b18d63dd04d
---

Core purpose of Cryptron, as the user stated it in July 2026 design sessions: the bottleneck he's automating is **not reasoning** — his reasoning already works (he demonstrated a full manual investigative loop over a Telegram-signal simulation: never accept the surface number → triangulate other senses → contrast winners vs losers → demand a mechanism → chase the driver behind the proxy → test transfer, refuse to overgeneralize → follow mechanism-guided curiosity). What fails is that his reasoning **starves**. Three human limits, none of them logical:

1. **Coverage** — can't watch every source in the world, 24/7.
2. **Memory** — even what he sees, he can't document and retain.
3. **Processing** — even what he retains, he can't hold it all in his head to reason over.

His words: *"my reasoning is useless when I don't have enough to reason about."*

He already built Cryptron once **without designing it properly and had to throw it all away** — that failed attempt is why the design-first rule (creature doc §6/§15: no implementation before the brain's data flow) exists. It's a scar, not a preference.

His one-line definition (July 2026): **"Cryptron is an investigator that documents its finds in an efficient way — still to be designed — so it can reason easily over good data."** So the undesigned hard part is the **shape of a "find"**: the unit of documented knowledge that must carry enough (mechanism, scope/condition, out-of-sample *and* market-adjusted evidence, updating confidence) to count as "good data," while staying efficient to store and retrieve. That design *is* the §15 #1 gate.

So the system automates the **fuel supply to reasoning**: sense everything, remember everything (esp. ephemeral data that can't be re-fetched — CMC votes, social buzz), retrieve the right slice — so a reasoner (an LLM running a catalog of **general research questions**: did it happen elsewhere? what if I change one atom? what kind of coin is it per other sources? what related info helps? etc.) has enough to work with. The LLM fits because it is the **inverse of the human**: tireless reasoner, no memory, no senses.

His sharpening (July 2026, during first live testing): **the retrieval unit is the PATH, not the fact.** Investigations are chains (did X → got Y → inferred Z → checked W); the Obsidian vault is a *graph DB* whose [[links]] are the edges of those chains, not human-readable docs. Retrieval = vector search finds the entry point ("what past situation resembles this?"), then the graph walk replays the trajectory — case-based reasoning over his recorded investigations. Full-injection (dump all guidance in every prompt) is only tolerable while memory is tiny; it must become selective retrieval before it grows. "Pulling everything was never the idea."

Corollaries:
- The general-question catalog dissolves the docs' hand-wavy "invent/creativity" (§7 move 4, §10): inventing = asking a general question this thread hasn't gotten, or importing one that paid off elsewhere — a search over a question-library, and the library is *learnable* (rank questions by what has paid off = the §10 "for-you feed", grounded).
- **Richer/independent fuel is also the cure for overfitting** — the price-only backtest loop overfit because it was starved of independent signal; the fix for starvation and the fix for overfitting are the same (broader, remembered, independent, cross-sense evidence).

**The operational vision (stated in full, 2026-07-17):** the working loop is (1) an
**outcomes knowledge base** — coins we KNOW won or lost, how (under which exit/organ),
plus the background the hands captured about them — feeding (2) **comparison experiments**
that draw conclusions, so that (3) **new signals are evaluated against that knowledge**.
The chat is where he guides what to compare, checks Cryptron's conclusions, and makes
sure the knowledge is built correctly — teaching and developing in the same conversation.
**End goal: Cryptron finds good opportunities on its own, using HIS evaluation
methodology** — saving his time/effort and extending his limited memory and capability.
The mindset for anything it sees: *is there an opportunity in this signal? do I know the
quality of this opportunity? did I have everything needed to assess it, or do I need more
tools?* — the self-check that both evaluates and grows the body.

**The guiding protocol (his pushback, same day — get this exact):** he tells Cryptron
**what to check, never what to conclude and never which thresholds matter** — cutting
lines ("100–500M cap coins with >70k watchlists took off") must be discovered by
Cryptron's own contrasts; he can't run the checks himself, that's why Cryptron exists.
His chat questions get a **gap-check, not auto-banking**: if Cryptron already
ran/considered the thing asked, answering from what it has IS the system working (over
time most questions should land there); only an uncovered question is a gap to close,
and only a general+new lesson gets saved — **"you don't want to save trash"** (memory
economy is a first-class rule). Verdicts summarize the FEW most decisive checks — never
information-bomb; he drills in for the rest. And Cryptron must end evaluations with a
**verdict** (good / bad / not enough to tell + checks done + checks not yet done) so he
can answer "you did enough" or "still need to check X" — verdict-first answers are also
how HE practices precise guiding ("you did good/bad because..."). Sometimes he just
wants a quick answer instead of visiting websites — that's a legitimate mode too.

**Why:** reorders build priority — the organs worth most are **senses + memory** (they beat his human limits); the reasoning loop rides on top, not the reverse. **How to apply:** when designing anything, ask "does this remove a human sensing/memory/processing limit?" before "does this make the reasoning cleverer?" Ties to docs §5 (embodiment) and §6 (memory). See [[user-role-cryptron]].
