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



## 2026-08-09 — First end-to-end run (UC1 pipeline, live writes)

- Duplicate detection: correct in code — #1 top with reasoning, #8/#2 demoted with failure-mode distinctions, #10 surfaced as "why no early warning" context
- Suspect commit: FAILED — Github.ListRepositoryActivities returns event IDs and actor only (no SHAs, messages, timestamps); can't support "what changed recently" triage. Model responded honestly: said it couldn't determine, listed what would help, hallucinated nothing. Fix: switch to a commits tool
- Stubs (on-call, claim impact) render seamlessly — must be live or narrated as stubs at demo



## 2026-08-09 — Availability ≠ authorization: the gap between "exists" and "will work"

- Three layers must align for a tool call to succeed: the tool exists in the catalog, the agent has it selected, and the user's grant covers the action. The platform answers the first two; nothing answers the third until the call fails
- The GitHub 403 is the proof: CreateIssueComment was available and selected, and still failed on the user's grant — discoverable only by attempting the write
- What a platform team would want: a pre-flight answer to "for this user, with these grants, which of the agent's tools will actually work?" Today that diff is computed by failing in production
- Design note on our agent: it uses static tool binding (six hard-coded tools) rather than runtime discovery. For a governed enterprise agent that's arguably correct — a reviewed, fixed tool list is auditable — but it makes the missing pre-flight check more costly: static agents fail at run time, not at configuration time



## 2026-08-09 — Static vs. dynamic tool binding: a design choice with governance weight

- Two moments of tool discovery in this build. At build time, the coding model probed tool schemas via the SDK (tools.get) and wrote code against verified names — discovery once, by the coder. At runtime, the agent calls six hard-coded tools and never asks what's available; a missing tool is a crash
- The alternative exists: the SDK supports runtime listing, so an agent could adapt to whatever tools it's granted. Ours deliberately doesn't
- For a governed enterprise agent, static binding is arguably correct: a fixed, reviewed tool list is auditable, and "the agent started doing something new without a review" cannot happen by construction. The cost is brittleness — configuration drift shows up as runtime failures instead of config-time warnings
- Governance framing for the platform: static agents make the missing pre-flight check (see availability ≠ authorization, above) more valuable, not less — the review happens once, so the platform should be able to validate the reviewed list against each user's grants before anything runs



## 2026-08-09 — Two writes, two outcomes: the Slack success and the GitHub dead end



### What happened

- The pipeline's approved run executes two writes. Slack: SendMessage lacked a posting scope from the earlier read-only consent — mid-run, the SDK printed an auth link, waited, and resumed after consent; the message posted as "Priya Raman," indistinguishable from the human typing, no agent marker in the system of record
- GitHub: CreateIssueComment failed with a raw upstream 403. Revoking the connection and re-consenting fresh completed "successfully" — the SDK challenge now fires and resumes, matching Slack's flow — and the write still 403s identically
- Overnight token refresh, for the record: all GitHub/Slack reads worked first-try after ~12h idle, no re-auth



### Why: GitHub's two-step authorization model

- GitHub apps have two separate grants: the user's personal consent ("act as me" — the screen we approved, twice) and the app's INSTALLATION on specific repositories with granular permissions (Issues: write, etc.). A write works only where both exist
- Arcade's flow performs the first step and never triggers the second. GitHub's own app page confirms it: "Never used" / "has not been installed on any accounts you have access to" — after two successful authorizations and two days of working reads
- No self-serve fix exists: the app page offers no Install button, the app is absent from GitHub's marketplace, and no Arcade surface (dashboard, error, docs for the managed app) links an installation flow. Arcade's own BYOC guide states installation is required ("you need to install it to make it functional") — the managed default app has no equivalent step anywhere
- Reads only appeared to work because this repo is public: they required no grant at all. On a private repo, the missing installation would have blocked the very first read — surfacing the problem at setup instead of at the first consequential write. Public-repo pilots are the treacherous case: everything demos until the moment it matters



### Sim vs. enterprise

- Here, employee and repo-owner are the same person (personal account). At a real F2000, repos live in a GitHub organization: the installation is a one-time org-admin act, and an engineer hitting this 403 is seeing "the admin hasn't approved the app for this repo" — with no way to self-serve past it, and an error that says none of this



### What it teaches

- GitHub's model is the security-correct one — Arcade's own docs praise it (fine-grained, admin-gated, audit-friendly). The gap is purely product: the managed flow never completes its own ceremony, and the error names neither the cause nor the fix
- The pattern generalizes: enterprise authorization is multi-party. The user's yes is never the whole story (GitHub: installation; Slack: workspace app approval; Google/Microsoft: admin consent). A platform pitching unified auth is pitching the absorption of exactly this heterogeneity — and this incident measures where absorption currently ends
- Practical corollary for any agent pilot: verify the write path on day one. Successful reads prove little; the first write is the real authorization test



### Status

- GitHub comment write: documented-as-blocked; support ticket to Arcade is the next step and its handling becomes part of the evaluation record. Slack write: fully working, behind the gate



## 2026-08-09 — Confirmed: no tool lists a repository's commit history

- Checked all 43 GitHub tools. Two touch commits at all: ListPullRequestCommits (commits inside one pull request) and GetUserRecentActivity (my own recent activity, across repos). ListRepositoryActivities sounds right but returns no commit messages, authors, or dates
- What this means in practice: there is no single call that answers "what changed in this repo recently?" Teams that merge everything through pull requests can piece the answer together — list recent PRs, keep the merged ones, fetch each one's commits — which works, but turns one question into several calls plus filtering logic
- What stays invisible: changes that never went through a PR — urgent hotfixes, admin pushes, bot commits, config repos with looser rules. These exist in most real organizations, and they're often exactly the changes behind an incident
- Our agent's workaround: read the current contents of the known config files and let the model compare them against what past incidents say a healthy state looked like. This can say "this setting looks wrong given history" — it cannot say "this change, made on this date, caused it." The file paths are hard-coded and marked as a simplification in the code
- Broader point: 43 tools and an "Optimized" badge read like full coverage, but this gap only shows up when a workflow needs it. Counting tools is not the same as covering workflows



## 2026-08-09 — Inference needs a baseline, and the baseline lives in comments

- With the regression present (max_runners now 8), config-state inference still couldn't call it: the model correctly said the values look "plausible but tight" and asked for git history — it had no way to know 8 used to be 16. Detecting a regression from current state alone is structurally impossible without a known-good reference
- The reference exists in our corpus: issue #1's resolution comment records that capacity was raised. But the agent reads issue BODIES (ListIssues); resolution comments are a separate object it never fetches. The most valuable sentence in incident history — how it was fixed last time — is invisible to the implementation as built
- Model behavior stayed exemplary: named both plausible mechanisms, refused to blame the YAML without evidence, and for the third run straight listed "check the git log" as its top recommended action — the agent keeps asking for precisely the tool the toolkit lacks

## 2026-08-09 (late) — Issue comments: the toolkit can write but not read
- Across all 43 GitHub tools, exactly one touches issue comments: CreateIssueComment (write). Four others handle pull-request review comments — code-review threads, a different object. No tool reads an issue's discussion, and GetIssue returns only the issue itself
- The asymmetry matters for triage specifically: teams close incidents with the fix in the final comment. An agent on this toolkit can post into that conversation but can never learn from it — and in our build the write was blocked too (the app-installation 403), so the issue conversation was unreachable in both directions: reads by toolkit design, writes by the authorization gap. "Closed issues are where resolved history lives" fails for any repo whose fix knowledge sits in closing comments rather than bodies (i.e., most repos)
- Workaround shipped: the agent identifies the closest past incident, prints a notice that its resolution comments are unreachable, and feeds its issue body verbatim into the analysis as the fullest available record
- Pattern across the day now visible: three adjacent gaps in one workflow — no repo commit history, activity events without metadata, comments writable but not readable. Each alone is a nit; together they mean the toolkit supports acting on the present but not learning from the past, which is half of what incident triage is

## 2026-08-10 — The one-Meridian-rule probe: roles don't exist yet, by the product's own admission
- Target rule (the AI Platform Lead's requirement, verbatim): "engineers on the incident-response rotation may post to Slack through agents; read-only engineers may not"
- Search of the dashboard: Members governs project collaborators (dashboard administration), not end users — Priya and Jordan aren't members at all, they're connected identities under Connections. No roles column, no permissions surface
- The Invite Member dialog states it directly: invitees get "full access to this project," with a sign-up link for "advanced roles" in preview. So: one access level today, role model acknowledged as future work by the product itself
- Verdict: the rule as stated cannot be expressed. The model stops at: no roles exist. The nearest available levers are per-agent tool selection (applies to every user of the agent equally) and per-user provider grants (per person, not per class) — a rule that binds a CLASS of users to a TOOL permission has no home between them
- Why it matters for the ICP: this is the first sentence an enterprise admin tries to configure. "Advanced roles in preview" says Arcade knows; the probe documents what the gap feels like from the buyer's chair today