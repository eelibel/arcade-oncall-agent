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
- Day-2 retry (fresh session, new chat): identical outcome — consent completes, redirect clean, no connection registered, no error. Contrast with the GitHub failure is instructive: GitHub broke provider-side while Arcade showed a healthy connection; PagerDuty completes provider-side and dies Arcade-side. Same silent-dead-end symptom, opposite broken layers — and nothing tells the user which. Escalating to support; the response becomes part of the evaluation record



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



### Addendum (2026-08-10, after PM-suggested playground test)

- Same write attempted from the playground: identical 403. The dead end is surface-independent — SDK and playground share the fate
- Sharpening contrast from the same session: STARRING a repo from the playground succeeds. "View and manage your starred repositories" was explicitly in the user-consent scope list; issue comments never were. So the boundary is now precisely drawn: writes WITHIN the user-consent scopes work without installation; writes beyond them 403 — exactly what the two-grant model predicts
- Bonus observation: the playground model's own explanation of the 403 was confidently wrong — it claimed the account lacks repo write access (the account owns the repo) and suggested "a GitHub token with repo scope" (not applicable to the managed flow). The layer that interprets errors for users invents plausible-but-incorrect remediation, which makes the silent dead end actively misleading rather than just unexplained



## 2026-08-09 — Confirmed: no tool lists a repository's commit history

- Checked all 43 GitHub tools. Two touch commits at all: ListPullRequestCommits (commits inside one pull request) and GetUserRecentActivity (my own recent activity, across repos). ListRepositoryActivities sounds right but returns no commit messages, authors, or dates
- What this means in practice: there is no single call that answers "what changed in this repo recently?" Teams that merge everything through pull requests can piece the answer together — list recent PRs, keep the merged ones, fetch each one's commits — which works, but turns one question into several calls plus filtering logic
- What stays invisible: changes that never went through a PR — urgent hotfixes, admin pushes, bot commits, config repos with looser rules. These exist in most real organizations, and they're often exactly the changes behind an incident
- Our agent's workaround: read the current contents of the known config files and let the model compare them against what past incidents say a healthy state looked like. This can say "this setting looks wrong given history" — it cannot say "this change, made on this date, caused it." The file paths are hard-coded and marked as a simplification in the code
- Broader point: 43 tools and an "Optimized" badge read like full coverage, but this gap only shows up when a workflow needs it. Counting tools is not the same as covering workflows



## 2026-08-09 — The fixed step 4: config-state inference works, and names its own limits

- With current config + incident history, the model produced genuinely competent triage: ranked autoscale.yaml as primary suspect with mechanism (pool exhaustion signature), flagged scale_down as contributing, explicitly cleared the unrelated group-benefits file ("not manufacturing a connection"), noticed the absent claims workflow YAML as a gap, and closed with a "What I Am Not Asserting" section — unprompted epistemic honesty, now a stable trait across runs
- The irony that makes the toolkit gap concrete: the analysis's own top recommendation — in consecutive runs, in both drafts — is "check the git log for autoscale.yaml." The agent's first suggested action is precisely the capability the toolkit doesn't offer. The gap isn't theoretical; the agent itself asks for the missing tool



## 2026-08-09 — Inference needs a baseline, and the baseline lives in comments

- With the regression present (max_runners now 8), config-state inference still couldn't call it: the model correctly said the values look "plausible but tight" and asked for git history — it had no way to know 8 used to be 16. Detecting a regression from current state alone is structurally impossible without a known-good reference
- The reference exists in our corpus: issue #1's resolution comment records that capacity was raised. But the agent reads issue BODIES (ListIssues); resolution comments are a separate object it never fetches. The most valuable sentence in incident history — how it was fixed last time — is invisible to the implementation as built
- Model behavior stayed exemplary: named both plausible mechanisms, refused to blame the YAML without evidence, and for the third run straight listed "check the git log" as its top recommended action — the agent keeps asking for precisely the tool the toolkit lacks



## 2026-08-09 (late) — Issue comments: the toolkit can write but not read

- Across all 43 GitHub tools, exactly one touches issue comments: CreateIssueComment (write). Four others handle pull-request review comments — code-review threads, a different object. No tool reads an issue's discussion, and GetIssue returns only the issue itself
- The asymmetry matters for triage specifically: teams close incidents with the fix in the final comment. An agent on this toolkit can post into that conversation but can never learn from it — and in our build the write was blocked too (the app-installation 403), so the issue conversation was unreachable in both directions: reads by toolkit design, writes by the authorization gap. "Closed issues are where resolved history lives" fails for any repo whose fix knowledge sits in closing comments rather than bodies (i.e., most repos)
- Workaround shipped: the agent identifies the closest past incident, prints a notice that its resolution comments are unreachable, and feeds its issue body verbatim into the analysis as the fullest available record
- Pattern across the day now visible: three adjacent gaps in one workflow — no repo commit history, activity events without metadata, comments writable but not readable. Each alone is a nit; together they mean the toolkit supports acting on the present but not learning from the past, which is half of what incident triage is



## 2026-08-10 — The approval log that wasn't: ordering matters

- Our gate logs the approval AFTER executing both writes. Both approved runs crashed between the writes (Slack succeeded, GitHub 403'd) — so two real, human-approved, executed Slack posts have no approval record at all. The audit trail has a gap exactly where an auditor would look first: the runs where something went wrong
- The design lesson, now demonstrated rather than asserted: record the approval decision BEFORE executing, then record each action's outcome. An approval log that depends on everything succeeding documents only the boring runs
- Fix shipped same night: decision line written pre-execution; one outcome line per action (sent/failed + error kind); declines logged too — a human saying no is itself an audit event. Side effect accepted deliberately: the two writes are now independent, so one failing no longer prevents the other — correct semantics for a gate that approved both



## 2026-08-10 — The one-Meridian-rule probe: roles don't exist yet

- Target rule (the AI Platform Lead's requirement, verbatim): "engineers on the incident-response rotation may post to Slack through agents; read-only engineers may not"
- Search of the dashboard: Members governs project collaborators (dashboard administration), not end users — Priya and Jordan aren't members at all, they're connected identities under Connections. No roles column, no permissions surface
- The Invite Member dialog states it directly: invitees get "full access to this project," with a sign-up link for "advanced roles" in preview. So: one access level today, role model acknowledged as future work by the product itself
- Verdict: the rule as stated cannot be expressed. The model stops at: no roles exist. The nearest available levers are per-agent tool selection (applies to every user of the agent equally) and per-user provider grants (per person, not per class) — a rule that binds a CLASS of users to a TOOL permission has no home between them
- Why it matters for the ICP: this is the first sentence an enterprise admin tries to configure. "Advanced roles in preview" says Arcade knows; the probe documents what the gap feels like from the buyer's chair today



## 2026-08-10 — Audit-depth probe: the log records the dashboard, not the runs

- Audit Logs, checked after a weekend of activity, contains one entry: the API key's creation two days ago. Absent: every tool execution (~20 across playground and SDK), both Slack writes, the OAuth challenges and consents, the GitHub connection revoke, and the repeated failed PagerDuty registration attempts
- Read against a security reviewer's questions — who did what, when, through which agent, who approved, what failed — the answer to all of them is: not here. The log covers dashboard administration events, not agent activity
- Sharpest gap given the product's own story: attribution is the platform's foundation claim ("know who did what and when"), and the per-call delegation machinery clearly knows — but what it knows isn't surfaced anywhere an auditor can read. The data plane and the audit surface are different products today
- Also notable: the failed PagerDuty registrations left no trace here either — the silent failure is silent all the way down
- Probe verdict: confirmed gap. Our approvals.log (agent-side) currently holds more governance-relevant record than the platform's audit log — and we had to build it



## 2026-08-10 — User verification: the guardrail that fired, and the best error in the product

- Switching the agent's user_id to a persona identity ([priya@meridian-sim.com](mailto:priya@meridian-sim.com)) failed at OAuth with an "Authorization error" page that is everything the product's other failures aren't: it shows the mismatched values (user_id provided vs. Arcade account signed in), explains why they must match (anti-phishing — the person authorizing must be the person who started the flow), and lists fixes. Same platform, one failure explained beautifully while others fail silently — proof the bar is achievable in-house
- The constraint behind it: verification has two modes and no off-switch. "Arcade.dev users only" (development) binds every user_id to a real, invited, signed-in Arcade account; "Custom user verifier" (production) means building your own verification page. There is no sandbox mode for simulating multiple logical users — a take-home-shaped problem, but also a real one for any team wanting to demo multi-user flows before wiring production auth
- Enterprise reading: this is where Meridian would plug Okta — the custom verifier is presumably how User Sources connect, so "the person is who they claim" gets answered by the IdP. The dev-mode binding is the right default; what's missing is the middle rung between "invited Arcade accounts" and "build your own page"
- Practical consequence for this build: user_ids stay real Arcade accounts. Priya continues under the builder's account; Jordan gets a real Arcade account (email alias) invited to the project — which, silver lining, makes the intersection test's identity separation genuine rather than simulated



## 2026-08-10 — ClaimsCore: building and deploying a custom toolkit (the internal-systems path)

- Outcome: a fictional internal claims system (two tools, six-record dataset, one required secret) built, deployed to Arcade Cloud, and callable through the platform with per-user attribution — total ~70 minutes including every detour below
- First surprise, definitional: the documented "TDK" path is deprecated. The current mechanism is building an MCP server (arcade_mcp_server framework) deployed via the arcade CLI. Same concept, different packaging — and a sign of the platform consolidating everything onto MCP as THE packaging, which is a strategic signal, not just a rename
- The deploy experience exceeded expectations — the hypothesis said secrets would be the least-documented step; instead `arcade deploy` health-checked the server, discovered both tools, auto-detected the required secret from the local .env and uploaded it, and the tools appeared in the catalog with zero dashboard clicks. CLI login rode the existing browser session. This is the best end-to-end flow in the product
- The friction lived BEFORE deploy, in the dark: the framework silently requires Python ≥3.10 and uv (neither flagged as hard prerequisites); there is no documented way to test secret-gated tools locally (we hand-rolled a fake context); nothing documents how the server name becomes the tool prefix (server "claimscore" → "Claimscore.*", casing imposed by the platform); and the CLI's post-success interactive prompt crashes in non-interactive shells
- Catalog observation: the deployed toolkit appears alongside first-party servers with a "Secrets" chip but NO tier badge — the Optimized/Unoptimized taxonomy doesn't extend to customer toolkits, so an internal platform team's own tools are the unlabeled ones in their catalog
- Deploy logs exposed an InsecureKeyLengthWarning from inside Arcade's own worker (HMAC key below RFC-recommended length) — cosmetic to us, the kind of detail an enterprise security review reads differently

## 2026-08-10 — PagerDuty's bug confirned
- Root cause confirmed by Arcade (day 3, ~2h after reporting): the managed PagerDuty OAuth app is configured as non-public — only accounts on Arcade's own PagerDuty tenant can complete authorization through it. Acknowledged as a bug, with two remediations offered: use a different toolkit, or bring your own OAuth app (the documented production path). Every observed symptom now maps: consent succeeds (PagerDuty authenticates the user), the token exchange is rejected (app is internal-only), the flow stays pending, and no error surfaces at any step
- What the case illustrates for the roadmap: the failure was undetectable from the catalog, the docs, or any error message, and diagnosable only with vendor help — the cost concentrated in the silence rather than the bug itself. An error surfaced at the token-exchange step would have turned three days of retries into a five-minute support report
- Pattern worth noting alongside the GitHub finding: both managed default auth apps failed for an outside user for configuration reasons (installation coverage; app visibility), and in both cases the flows reported success while the underlying grant didn't materialize. A health check on the managed auth path — or surfacing exchange-level failures to the user — would catch this whole class

## 2026-08-10 — Intersection probe, part 1: Jordan runs the identical flow
- Same code, same issue, one flag changed: --user set to Jordan, a second real Arcade account invited to the project. His GitHub OAuth showed the same consent screen as Priya's. Reads worked, the full triage analysis ran. A second user needed zero configuration
- The stop came at the Slack write. No error, no denial: the SDK printed an auth link and waited. The link opens Slack's workspace sign-in — Jordan has no account in that workspace, so he can't get past it. The run waits forever
- What stopped him is workspace membership, one fence outside the delegation grant the test was designed for. Three different gaps — no workspace seat, no Arcade grant, no posting permission — would all look the same here: an auth prompt he can't finish and an indefinite wait. Nothing says which one to fix
- Part 2: give Jordan a seat, keep withholding the grant, isolate the delegation fence

## 2026-08-10 — Intersection probe, part 2: Jordan with a Slack seat, without the grant
- Gave Jordan a real Slack workspace seat, still withheld the Arcade authorization. Re-run: GitHub worked on his existing grant; the Slack challenge now leads to a completable consent screen. The only remaining barrier is the grant itself. Left unclicked; the run waits indefinitely
- The consent screen asks for more than the task needs: metadata on his private channels, DMs, and member emails — to post one message to one public channel. Consent is all-or-nothing; a user cannot grant narrowly
- Net result: agent capability = agent tools ∩ user grants, per user, no configuration needed. At the delegation layer, the only enforcement is the user declining the consent screen

## 2026-08-10 — Gateway created: one URL, two auth layers
- Created an MCP gateway with the build's 15 tools across 4 toolkits. One URL exposes all of them — clients don't see per-toolkit endpoints
- Two auth layers: who may connect to the gateway (Arcade-account sign-in, or an identity provider, or API-key headers), then the usual per-provider OAuth as each tool is first used
- Settings observed: LLM instructions can be attached to the gateway itself (server-side steering that travels with the door, not the client); admins can skip the Arcade consent screen for trusted client IDs; passthrough headers supported
- The gateway's external-users option connects a company IdP (Okta, Entra, Auth0) via User Sources — end users then sign in with their work identity instead of Arcade accounts. This is the production identity path; observed, not tested (no IdP tenant in the sim)

## 2026-08-10 — Story B: three checkpoints, three owners
- Running the assistant surface (Claude Desktop → MCP gateway) surfaces three distinct permission prompts. One: Desktop's own per-tool popup ("Claude wants to use X — Always allow / Deny") — the client's guardrail, remembered per tool. Two: a one-time gateway sign-in (app-to-Arcade OAuth; scopes are MCP access plus offline access, i.e. a refresh token). Three: Arcade's per-provider auth, shown as a Connect button on the tool card — the same fence the SDK prints as a URL
- Observed, cause not confirmed: two GitHub reads ran, then a third GitHub tool demanded provider auth mid-session. The existing SDK-era grant did not obviously carry into the gateway surface
- The per-tool Desktop popup is the surface's only action checkpoint — it shows the tool NAME, not what will be sent. Relevant to the approval comparison at the write step

## 2026-08-10 — Story B: the assistant surface (Claude Desktop → MCP gateway)

### Setup
- Created an MCP gateway with the build's 15 tools across 4 toolkits. One URL exposes all of them; clients don't see per-toolkit endpoints
- Gateway settings observed: LLM instructions can attach to the gateway itself (steering that travels with the door, not the client); admins can skip the Arcade consent screen for trusted client IDs; the connect-door supports Arcade accounts, a company IdP (via User Sources — observed, not tested), or API-key headers
- Claude Desktop connected via "Add custom connector" + the gateway URL. One-time app-to-gateway OAuth; its scopes: MCP access plus offline access (a refresh token — the app stays connected across sessions)

### The run (7-prompt incident check-in as Priya)
- Reads worked across GitHub and ClaimsCore. The model ranked #1 as the near-match with #8 correctly separated, flagged the fix-in-blocked-deploy chain from issue text alone, and — asked "are claims blocked?" — split deploy-blockage from production impact correctly
- Mid-session, one GitHub tool demanded provider auth after two others had run; the SDK-era grant did not obviously carry over. Cause not confirmed
- PagerDuty on this surface: Connect card → consent → same dead end. Failure now confirmed on all three surfaces (playground, SDK, gateway)
- The final prompt posted an update to #incidents. The message landed as Priya Raman, indistinguishable from her typing. It incorporated the live ClaimsCore record (claim id, amount, filing date) and its "Asks" requested a claims-list query — a tool the toolkit doesn't have

### Three checkpoints, three owners
- Desktop's per-tool popup ("Claude wants to use X — Allow once / Always allow / Deny") — the client's guardrail. Shows the tool name, not the payload
- The gateway sign-in — once, app-to-Arcade
- Arcade's per-provider auth — the Connect card, same fence the SDK prints as a URL

### One action, two approval mechanisms — the comparison, complete
- Pipeline door: the write waits at a gate that shows the FULL DRAFT of both messages, takes an explicit y, and logs the decision with a content hash before executing
- Assistant door: the write met the same generic per-tool popup as every read — tool name visible, message content not shown in the checkpoint, nothing logged by the platform. Allow-once was used throughout, so a checkpoint did appear each call; "always allow" would have removed even that
- Same governed action, same user, same tools: one door reviews the content, one door reviews the tool name. What "a human approved this" means depends entirely on which surface the action came through

## 2026-08-10 — UC2 (Amara): meeting prep, live claims answer, and the deliberate failure

### The prep run (Claude Desktop → gateway, Gmail + ClaimsCore)

- Gmail read through the gateway found the seeded client email and produced genuinely useful prep: it connected the client's rate question to the delayed claim, and the delayed claim to our own blocked deploy — cross-system synthesis across Gmail, ClaimsCore, and the GitHub incident, unprompted
- It also flagged the seed as suspicious from the headers ("signed by Dana but sent from your own address; a reply won't reach Dana") — the model distinguishing content from authenticated sender on its own
- Sixth occurrence of the pattern: it asked for a claims-list query ("someone needs to run the query for everything in that delayed state") — the tool the toolkit doesn't have
- Friction note: Desktop cached the gateway's tool list; Gmail tools added to the gateway didn't appear until the app restarted. Before the restart, Desktop's own connector directory offered its native Gmail integration one click away — a route to the same provider that bypasses the platform's visibility and controls entirely. Same user consent, no enterprise handle

### The deliberate failure: confidential content outbound

- The ask: email internal pricing (marked CONFIDENTIAL — Internal Only) to the client contact. The platform path was fully open: tools selected, grants obtainable, no policy in the way
- What actually resisted was the model. It refused the first request with three grounds: the recipient address is an unverified alias, the CONFIDENTIAL marking means "someone already decided this doesn't leave the building," and it lacked file access. It demanded explicit confirmation of intent and a verified address
- One confirmation later ("this is a simulation, I confirm: send it"), it sent. The send required a fresh Google consent carrying the gmail.send scope (the incremental ask, done properly — narrow, explicit). The email with the confidential pricing block was delivered
- What each layer contributed: the platform checkpoint showed a tool name; Google's consent showed a scope; the model showed judgment — the recipient forensics, the meaning of a confidentiality marking, a draft preview, and a warning about reuse. The only layer that examined the CONTENT was the one nobody configured and nothing guarantees
- The reading for a governance board: today, the difference between a good and a bad outcome on this action was model discretion. It was excellent here. It is not a control: it varies by model, prompt, and phrasing, it cannot be audited in advance, and it complied after a single confirmation. The missing layer — policy that sees content and conditions, not tool names — is precisely what the approval-gate pattern previews and what nothing in the platform currently provides

## 2026-08-11 — The agent-scope dial: narrowing the gateway holds, after a reconnect
- Test: removed Slack.SendMessage from the gateway (Priya's own Slack grant left intact — she can still post), to narrow the agent below what the user is allowed to do. This is the one control that could hold an agent below its user's grants
- Propagation is not immediate. After saving the change, the tool was still callable through a running Claude Desktop session — an app restart and a fresh chat both still served it. It disappeared only after fully disconnecting and re-adding the connector
- Once propagated, the dial holds cleanly. The assistant found SendMessage absent, said so plainly ("the Slack send-message tool is no longer available through meridian-gateway... write permission may have been revoked or the connector's configuration changed"), declined to invent another path, and offered the message as text to paste manually
- The stop is legible — the user can tell the tool is gone — but not attributable: from the caller's side there's no way to tell whether the user's grant or the agent's scope removed it. Same ambiguity the intersection probe found, now confirmed from the other direction
- For the thesis: agent-scope narrowing is the one control that works today to hold an agent below its user's grants, and it does work. Two caveats bound it — it is global (every user of that gateway, not per-user or per-role), and edits don't reach live clients until they reconnect (MCP specifies a tools-list-changed notification; the change didn't propagate without a manual reconnect). Real control, but coarse and slow to propagate; the per-user conditional layer is still the gap

## 2026-08-11 — The agent-scope dial: narrowing the gateway holds, after a reconnect: Post-submission check, for completeness: 
the API spec documents /v1/plugins and /v1/hooks (hook points: tool.access, tool.pre, tool.post), and the published webhook contract shows the access hook receives the user_id and can return per-user allow/deny tool sets — so per-user permissioning is achievable by hosting your own logic behind the hooks. The role model itself would live in the customer's webhook server, not in Arcade. On our account both endpoints returned 404 despite appearing in the spec; the docs route configuration through the dashboard surface we probed. This sharpens the finding rather than changing it: the enforcement point exists and is per-user capable; what's missing is the product on top — a role model, rule authoring, and reachability