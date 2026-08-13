# arcade-oncall-agent

A take-home build for Arcade: two working agent use cases for a fictional
Fortune-2000 insurer, built as an outside developer, with every finding,
decision, and prompt logged in the open.

**The scenario:** Meridian Mutual Insurance — a fictional F2000 insurer.
An on-call platform engineer (Priya) uses an agent for incident triage; a
client executive (Amara) uses one for meeting preparation; a third user
(Jordan) exists to test what happens to someone the setup never
anticipated. The full scenario — company, personas, use cases, and the
test list — is in [meridian.md](./docs/meridian.md).

A recording of the setup and the pipeline run: https://drive.google.com/file/d/120ZGqK972Q7zSDXXMXo1jurQJ5g-7iA_/view?usp=drive_link

## What's here

| File / folder | What it is |
|---|---|
| [findings.md](./process/findings.md) | The evidence: ~30 dated product observations from building on Arcade |
| [decisions.md](./process/decisions.md) | Every decision that changed course, with its reasoning |
| [prompts.md](./process/prompts.md) | Every instruction given to the coding AI, and what came back |
| [meridian.md](./docs/meridian.md) | The fictional company, personas, use cases, and test design |
| [roadmap-deferred.md](./roadmap-deferred.md) | Deferred roadmap slices with reasons and triggers (referenced by the strategy doc) |
| `agent/` | The triage agent: a governed Python pipeline with a human approval gate |
| `claimscore/` | A custom internal system (two tools), deployed to Arcade as an MCP server |
| `process/cursor-sessions/` | Unedited exports of the AI coding sessions |

## The two use cases

1. **Incident triage (pipeline).** A Python agent reads a live GitHub
   incident, searches history for duplicates, checks config state, pulls
   the affected claim from ClaimsCore, drafts a Slack update and a GitHub
   comment — then stops at a human gate that shows the full drafts and
   logs the decision (with a content hash) before executing anything.
2. **Meeting prep (assistant).** The same tools served through an Arcade
   MCP gateway to Claude Desktop: reads a client email, connects it to
   the delayed claim and the blocked deploy, and drafts the reply — with
   the platform's own checkpoints as the only controls.

Same actions, two doors — the difference between the doors is one of the
build's central findings. Both use cases in full:
[meridian.md](./docs/meridian.md).

## Running it
./venv/bin/python agent/triage_agent.py 11
./venv/bin/python agent/triage_agent.py 11 --user <arcade-account-email>

Requires an Arcade API key in `.env` and the toolkits authorized for the
running user. The approval log (`approvals.log`) is written locally and
deliberately not committed. The PagerDuty on-call lookup is stubbed: the
managed PagerDuty auth app cannot complete authorization for outside
users (confirmed by Arcade as a bug); production would bring its own
OAuth app.

## How this was built: the AI workflow

This project was built in four days by one person working with three AI
systems in deliberately separated roles.

**Two strategy chats with distinct jobs.** One chat (Claude) held the
strategic layer: competitive context, interview intelligence, framing
decisions. A second chat (Claude) ran the build: stage-set setup, live
testing, findings capture. The separation was a confidentiality valve —
the build chat's outputs feed this public repo, so nothing
conversation-sourced was allowed to enter it. Everything in findings.md
is direct observation.

**A coding agent under supervision.** The agent code, the custom
ClaimsCore toolkit, and every fix were written by an AI coding assistant
(Claude models, in Cursor), with command execution kept on manual
approval throughout. Every prompt given to it, and what came back —
including its failures — is logged in prompts.md.

**Working rules that shaped the output.** Findings were written the
moment they happened, never reconstructed later. Hypotheses were declared
before the build began and tracked to resolution. Every decision that
changed course is in decisions.md with its reasoning. Nulls and dead ends
were recorded as results, not deleted.

**What the process accidentally demonstrated.** The build kept exhibiting
the same governance patterns it was studying: the coding agent proposed
commands and a human approved each one; the agent masked secrets in its
own output unprompted; and our first approval log had the same
act-before-record flaw we later found in the platform's audit surface —
we fixed ours the same night.

**The assistant door.** Use case 2 (and the second half of use case 1)
runs through an Arcade MCP gateway connected to Claude Desktop: create a
gateway in the Arcade dashboard with the toolkits above, then add its
URL in Claude Desktop as a custom connector (Settings → Connectors).
Per-provider authorization prompts fire on first tool use. The exact
prompts used for the runs are in
[docs/run-scripts.md](./docs/run-scripts.md).