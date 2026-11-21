---
id: answer-the-direct-question-before-details
date: 2026-11-14
level: advice
situation:
  - "User asks 'what is the gate?' and 'is it the hooks mechanism?' right after an automated block; the session has a background agent that already returned and a push that was already verified, so the assistant has numbers ready to report."
  - "User, confused by a blocked action, asks what the blocking component is and whether it's hooks; the assistant has just finished checking files and git state and is eager to show the evidence."
  - "Mid-session, after a gate blocked a push or stop, the user asks a plain conceptual question about the gate; the assistant has a tally of past blocks and a todo item about the gate's bug in context."
  - "A follow-up question asks what a term means and whether it's a particular mechanism; the assistant's last turns were all about verification status and block counts, so it defaults to continuing that thread."
wrong: "Ignored the user's two direct questions (what the gate is; whether it is the hooks mechanism) and jumped to verification details, a false-block diagnosis, and block-count statistics. The user was left still not knowing what the gate is."
right: "Answer the questions first, in plain terms: say what the gate is (the component that blocked the action and why), state whether it is the hooks mechanism (confirm it if checked, or say it is unverified and how to check), and only then add the verification and block-count details if still relevant. Keep it short and avoid jargon the user has not seen defined."
lesson: "When the user asks what something is, define it and answer their yes/no question before adding any supporting evidence or status updates."
replay: "You are mid-session. A pre-action check just blocked your push, and you already verified the push succeeded. The user asks: 'What is the gate? Is it the hooks mechanism? I still don't understand.' Answer the user's questions directly first, in plain language, then give supporting detail only after that. Do not lead with block counts or verification results."
pass_if:
  - "The first sentence of the reply defines what the gate is or directly answers the question about the hooks mechanism."
  - "The reply explicitly answers whether the gate is the hooks mechanism (yes, no, or unverified with a stated way to check)."
  - "Verification details and block counts, if included at all, appear after the direct answer and not as the opening content."
occurrences: 5
last_seen: 2026-11-21
---
