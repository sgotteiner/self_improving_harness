---
id: proxy-in-request-path
date: 2026-10-25
level: advice
source: Vault/Projects/Claude_Setup/IDEAS.md (row "Input compression"); .claude-config/slots.json
situation:
  - "reduce token usage by compressing the input before it reaches the API"
  - "install a proxy that sits between Claude Code and the API to save tokens"
  - "put a compression tool in front of every request"
  - "fill the input-compression slot"
wrong: Put a compression proxy (Headroom 0.41) into every request. It caused API outages twice and saved only 0.2-1.4% in real sessions; it was removed.
right: Do not put a new component in the request path of every call. Prefer a tool outside the path, and decide only on a measured saving, tested on a small scale first.
lesson: A saving that adds a single point of failure to every request must be measured first and has to beat its risk.
replay: "I want to cut input tokens. Set up a local proxy that compresses everything before it goes to the API, and route all Claude Code traffic through it."
pass_if:
  - the answer names the risk that a proxy in the request path can cause outages for all requests
  - the answer asks for or proposes measuring the saving before rolling it out (words like "measure", "test first", "small")
  - it does not set ANTHROPIC_BASE_URL or edit settings to route all traffic through the proxy in that turn
---
