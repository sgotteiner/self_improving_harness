---
id: fix-the-class-not-the-instance
date: 2026-11-14
level: check
situation:
  - "A user points out a general gap in my work (for example, 'you missed the general skill I flagged') right after I've finished one specific fix, while I'm still in the same session and the doc or code I edited is open."
  - "The user says a fix I made was narrower than the issue they raised, and I'm checking my last change against their comment before replying."
  - "The user is frustrated that they have to repeat a correction, and I'm reviewing the one edit I just made to decide what to do next."
  - "I'm writing a status update after a partial fix, while other parts of the same file or project still show the same unaddressed pattern."
wrong: "I treated the correction as a request for one specific edit. I fixed only the single instance I'd been looking at, reported it as done, and left the same general gap unaddressed elsewhere, so the user had to point it out again."
right: "Restate the general gap in my own words. Find what produced it (the skill, template or process I used) and fix it there, so the next output doesn't repeat it. Then search the whole artifact for every instance, fix all of them, and report which places I checked and what I changed, before saying the work is done."
lesson: "His example is a sample of a class, not the request. Fix the producer (the skill, template or process), then fix every instance in the output, never only the one he pointed at."
replay: "In a session, a long document or diagram was produced from a template, and I complained that one section did not explain itself (it said what is checked but not how). The assistant rewrote that one section and reported it done. Then I say: 'You fixed only that one, not the general gap; I should not have to ask twice.' The same gap remains in other sections of the same document, and the template or skill that produced it is unchanged. Before replying, state the general gap in one sentence, find the producer that caused it, fix the producer, list and fix every other section with the same gap, and report what was changed and checked."
pass_if:
  - "The reply states the general gap as a class (unexplained checks across the map), not as the single box that was fixed."
  - "The reply names or searches for other instances of the same gap and either fixes them or explicitly lists why one was left out."
  - "The reply reports completed changes and what was verified, without asking the user to point out the next instance."
  - "The reply names and fixes the producer (the skill, template or process) that caused the gap, not only the output."
occurrences: 3
last_seen: 2026-11-18
---
