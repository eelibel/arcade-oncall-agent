# Prompt log

Vibe-coding history for this build. Model: claude-fable-high in Cursor. Each entry: the prompt (or its essence), what came back, whether it worked. Failures and re-prompts are logged deliberately — they're where the product observations come from. Secrets and pure repetition are cut; nothing else is.

Entry format:

[session N] — short label

Prompt: what I asked (verbatim if short, essence if long) Result: what came back, in a line or two Outcome: worked / broke because X / re-prompted with Y

## [session 2] — Spine 1 happy path, Cursor + Fable

**Prompt:** Full build spec for agent/triage_[agent.py](http://agent.py) — pipeline triage agent per docs/[meridian.md](http://meridian.md): arcadepy for tools, Anthropic API as brain, 10-step flow, both writes behind one y/n gate, approvals.log with draft hash. (Full text in cursor-sessions export.)

**Result:** Fable started with careful reconnaissance — listed folders, checked .env exists via `sed` masking (never read key values), read .gitignore to confirm .env is protected before touching keys.

**Outcome:** in progress. Positive note: the masking behavior is exactly what you'd want an agent handling secrets to do.

## [session 2] — command approval kept manual

**Prompt:** (decision, not a prompt) Cursor offered "always approve" for terminal commands; declined.

**Result:** Every command gets a human look while the build involves live writes to Slack/GitHub.

**Outcome:** deliberate — the same agent-proposes/human-approves pattern this build exists to demonstrate.

## [session 2] — schema introspection before code

**Prompt:** Fable probed all 6 tools' parameter schemas via arcadepy before writing the agent.
**Result:** Real param names captured (state is optional string → must pass "all"; SendMessage takes channel_name). Two quirks: bare load_dotenv() crashes under heredoc (dotenv bug — explicit ".env" path fixed it); venv landed on python 3.9.
**Outcome:** worked — code written against verified schemas, not guesses. agent/triage_agent.py exists; gate verified by eye (both drafts shown, writes only after y, sha256 approval log).

## [session 3] — step 4 rebuilt twice, two toolkit gaps confirmed

**Prompt:** Fix suspect-commit analysis (activities tool has no metadata) → introspect for a commits tool → none exists (43 checked); fallback to config-state inference. Then: model can't detect regression without baseline → introspect for comment reading → write-only. Fallback: closest incident's body verbatim + printed notices.
**Result:** Both introspections definitive; both fallbacks shipped with SIMPLIFICATION comments; compile clean. Fable's introspect-before-code habit produced two evidence-grade findings.
**Outcome:** worked — and the failures were the deliverable.

## [session 3b] — approvals.log ordering fix
**Prompt:** Record the approval BEFORE executing (the two approved runs left zero trace — crash between writes ate the log). Per-action outcome lines; declines logged too.
**Result:** Decision line written pre-execution; each write in its own try/except with outcome + error_kind; n now logs a decline instead of exiting traceless. Side effect accepted: writes are now independent — one failing no longer prevents the other.
**Outcome:** compile-clean; validation on next live run.