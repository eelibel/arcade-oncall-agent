# Decision Log

This file is the chronological build log and choices made during this build, in chronological order.

- Use case & customer: see /docs/meridian.md. 
- Product observations: see /process/findings.md.

## 2026-07-30 — Repo setup

- Structure: /agent (code), /docs (architecture notes), /process (vibe-coding history, prompts, decisions)
- Rationale: assignment asks for generated markdowns + conversational history in a designated folder

## 2026-07-30 — Model selection

- Chose Claude Fable 5
- Rationale: current frontier model, strongest tool-calling reliability; model choice itself is a product-strategy question for Arcade's ICP — noted for the write-up



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

