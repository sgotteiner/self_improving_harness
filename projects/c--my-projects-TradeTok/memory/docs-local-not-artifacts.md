---
name: docs-local-not-artifacts
description: "Owner wants documents as local files he can open in VS Code, not Claude Docs or artifacts"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 1e9aa722-734b-4f0b-b4a5-ff0e86f0af33
  modified: 2026-11-01T14:47:54.596Z
---

Make documents as local files inside the project folder, not Claude Docs or other online artifacts, unless he asks for one.

**Why:** On 2026-11-01, after a Claude Doc was created for the StockerTV business map, he learned the VS Code extension doesn't reliably show artifacts and said: "if its not here i dont like it".

**How to apply:** Default to Markdown under the project's `docs/`, with diagrams saved as image files beside it. The business map's main copy is `C:\my_projects\stockertv_agents\docs\StockerTV_Business_Map.md`. Related: [[cto-learning-goal]].
