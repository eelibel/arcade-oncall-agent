# Decision Log
This file is the chronological build log and choices made during this build, in chronological order.

- Use case & customer: see /docs/meridian.md. 
- Product observations: see /process/findings.md.

## 2026-07-30 — Repo setup
- Structure: /agent (code), /docs (architecture notes), /process (vibe-coding history, prompts, decisions)
- Rationale: assignment asks for generated markdowns + conversational history in a designated folder

## 2026-07-30 — Model selection
- Fable writes the code (Cursor) - rationale: current frontier model, strongest tool-calling reliability; model choice itself is a product-strategy question for Arcade's ICP — noted for the write-up
- claude-sonnet-4-6 runs the agent (Anthropic API)
- Arcade's playground uses its own undisclosed model — playground results and agent results aren't strictly comparable

## 2026-08-03 — Session: env setup part 1
- Concept locked (Meridian incident triage); catalog recon done → findings.md
- meridian-platform seeded: 3 commits (16→8 suspect on top), first 6 issues, dup closed w/ root cause
- Next: corpus →10, Slack, PagerDuty, second account, Arcade

## Personas & accounts (disclosure)
- Cast is fictional; two real test accounts run everything
- Primary account plays Priya (later Amara); secondary plays Jordan
- Marco & Katherine are names only (Marco = PagerDuty rotation; Katherine = intended approver in the enterprise pattern)
- Today's gate self-approves; routing approval to a separate person/policy system is the gap this build documents

## 2026-08-08 — Session: env setup part 2
- 10 issues live (IdP refs → Okta); Slack #incidents up; PagerDuty schedule verified (Priya→Marco 6pm); API key funded
- Arcade: no per-app connect step — auth happens at first tool call. Playground test pending
- Next: verify 3 toolkits, risk test 1, Spine 1

## 2026-08-08 — Decision: use cases finalized
- UC1 incident triage (platform team dogfood), UC2 client servicing (Amara)
- Live incident carries a claims-intake hotfix in the blocked deploy — links UC1 to ClaimsCore honestly

## 2026-08-08 pm — Session: playground verification + pre-build check
- GitHub + Slack connected and verified from the playground; PagerDuty fails silently — parked, on-call lookup stubbed
- Pre-build check passed (UC1 duplicate detection works)
- Next: PagerDuty retry (5-min cap), then UC1 happy path in Cursor

## 2026-08-08 late — Session: agent built
- Cursor Pro upgraded (free tier gates model choice — noted); Fable wrote agent/triage_agent.py against introspected schemas
- Approval gate verified in code; [RUN RESULT: fill A or "first run pending"]
- Next: [A: UC1 tests / B: first run], then Story B, UC2, ClaimsCore

## 2026-08-10 — user_id stays bound to real Arcade accounts 
User verification requires it; persona ids can't pass. Jordan = separate Arcade account via alias; Priya = builder's account, disclosed in meridian.md

## 2026-08-10 — TDK is deprecated; 
ClaimsCore built on the current path (MCP server framework + arcade deploy). Canon references to "TDK" read as "custom MCP toolkit"

## 2026-08-10 (evening) — UC2 complete; 
rules probe complete (pipeline exists, rules are BYO webhooks). Declined: building a demo rule service (proves webhook-writing, not product insight) and BYO PagerDuty OAuth (finding closed, stub suffices). Two-fences dial → Tuesday AM