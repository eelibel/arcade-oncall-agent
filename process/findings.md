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

## 2026-08-08 — First tool calls from the Arcade playground: GitHub, Slack, PagerDuty
- Tested the first connection to each of the three providers. GitHub and Slack connected and returned data. PagerDuty failed — details in the next entry
- The three OAuth consent screens are very different experiences. GitHub asked for account-wide access with no way to pick a repo, and requested write permissions (starring, watching) plus my email for what was a read-only call. Slack showed an "App is not approved by Slack" warning and asked to read other workspace members' email addresses. PagerDuty had the cleanest screen: granular, per-resource, everything explicitly read-only. These screens are what a customer's security review sees, and the inconsistency is the point — even though the scopes are set by each provider, not by Arcade
- First GitHub ListIssues call failed: the playground model sent search_org_wide=null and the tool rejected it. The retry sent false and worked. Lesson: optional parameters don't accept null
- ListIssues only returns open issues unless you explicitly ask for state="all". A triage agent that forgets this cannot see closed incidents — meaning no access to resolved history. Found this before writing any code
- After authorizing a provider, the interrupted call does not resume — you have to send the prompt again. True for both providers that connected

## 2026-08-08 — PagerDuty connection fails silently
- The consent screen completes on PagerDuty's side and the browser redirects back cleanly — but the connection never appears in Arcade's Connected Users list, and no error is shown anywhere. There is nothing for the user to act on
- Tried: a new playground chat, re-authorizing three times, logging out and back in, a fresh consent flow. The billing page shows no connection limit (quotas barely touched), and the "user challenges" counter did increment — so Arcade saw the attempts
- My first self-debugging theory (I used a different email domain for PagerDuty than for the other tools) turned out to be wrong — but nothing in the UI told me that. Silent failures make users invent explanations
- Parked for now: the agent will use a hard-coded on-call answer until this resolves; retrying next session. If it persists, I'll open a support ticket

## 2026-08-08 — Pre-build check (UC1): can GitHub search actually find the duplicate incident? (playground, model-driven search)
- Context: the most load-bearing assumption in UC1's value story is that historical duplicates are findable. Tested it before writing any code, using the playground model + Github.ListIssues; the coded agent will re-run the same check
- Prompt: find past incidents similar to the live CI-timeout incident's wording, closed issues included
- Result: correct. Issue #1 (the planted near-duplicate) ranked top, with reasoning; #2 and #8 were correctly demoted with the right failure-mode distinctions; #7 surfaced as related; the response ended with a sensible next-step recommendation
- Mechanics: the model ran open and closed searches in parallel; one call failed on the null-parameter issue and self-retried
- Verdict: GitHub search quality carries the triage value story. No flow adjustment needed

