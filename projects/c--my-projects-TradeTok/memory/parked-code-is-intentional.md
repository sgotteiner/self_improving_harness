---
name: parked-code-is-intentional
description: "TradeTok's unused/commented-out pages and components are deliberately parked by the user, not dead code to report or remove"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 3a98222b-8bcc-4d23-b983-3480532fcc6e
  modified: 2026-10-14T18:12:00.762Z
---

In TradeTok, unimported components and pages switched off in App.tsx / Landing.tsx (Auth, Portfolio, Watchlist, Gift, IssuerDashboard, CompaniesPath, OnboardingFlow, etc.) are kept on purpose so features from earlier strategy phases can be brought back.

**Why:** the user said (2026-10-14) "im not talking about dead code i left so i could maybe get it back" after a code-quality review counted them as dead code.

**How to apply:** in code reviews of TradeTok, don't count parked code as a defect or propose deleting it; review only live code (duplication, type escapes, file size, the "Dev Bypass" auth redirect, etc.).
