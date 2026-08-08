# Findings

Product observations from building on Arcade. These feed the strategy doc.

## 2026-07-30 — Catalog recon: three toolkits, three maturity levels, one badge

- GitHub v4.1.0 / 43 tools incl. writes · Slack v2.5.4 / 10 tools · PagerDuty v0.3.0 / 14 tools, ALL read-only — yet all carry the same "Arcade Optimized" badge
- Badge = provenance, not readiness. A platform team can't tell from the catalog whether their workflow is expressible
- PagerDuty: everything needed to understand an incident, nothing to act on one (no ack/resolve/create). Read/write asymmetry tracks blast radius — deliberate or build-order artifact?
- Slack gap that bites: no message search — agent can only read channels it's pointed at



## 2026-07-30 — GitHub toolkit = what mature looks like

- CreateFile: explicit CREATE vs OVERWRITE mode — destructive path is opt-in at the tool boundary
- Assignment/label tools fuzzy-match — absorb model imprecision instead of failing
- Tool descriptions do error-prevention (CreateReviewComment documents the 422 case + fallback) and steer agent behavior ("DO NOT CALL MULTIPLE TIMES")
- GetReviewWorkload / GetUserOpenItems aren't GitHub API endpoints — composed, intent-shaped tools. Arcade authors a surface, doesn't wrap an API



## 2026-07-30 — Catalog structure observations

- Same service ships twice: hand-built Optimized + auto-generated "API" (Unoptimized) — no in-product guidance on which to pick. Open check: does PagerDuty API (Unoptimized) have the writes the Optimized one lacks? If yes, gap = discoverability, not capability
- Category placement inconsistent (PagerDuty in Dev Tools AND Customer Support; Linear/Jira outside Dev Tools)
- Velocity: ~2 dozen servers added in ~3 months; breadth compounding faster than depth
- Sentry absent entirely; Splunk/GitLab/Bitbucket/Okta coming soon
- Open check before designing the approval step: does Contextual Access already support agent-proposes / human-approves?



## 2026-08-08 — "Active" ≠ connected

- Looked for a "connect my accounts" button; doesn't exist
- Connected Apps shows providers "Active" = available, NOT user-connected
- Real model: connection created at first tool call (OAuth fires then)
- Model is right (just-in-time, per-user); dashboard doesn't say it — first-time platform engineer will hunt for the button like I did