# Roadmap appendix — scoring matrix and deferred slices

Two things the strategy document points to: the full scoring matrix
behind the 90-day ranking, and every deferred slice with its reason and
trigger. Derived from the findings in this repo (see
[findings.md](./process/findings.md)).

## 90-day theme scoring (full matrix)

Scored ● yes = 2 · ◐ partly = 1 · ○ no = 0, against four questions:
blocks enterprise deals / hurts current customers / differentiates /
proves the vision.


| Theme                         | Blocks deals | Hurts customers | Differentiates | Proves vision | Score |
| ----------------------------- | ------------ | --------------- | -------------- | ------------- | ----- |
| Approval & Rules              | ●            | ◐               | ●              | ●             | 7     |
| Scope                         | ●            | ○               | ◐              | ●             | 5     |
| First-connection & legibility | ◐            | ●               | ●              | ○             | 5     |
| Receipts                      | ●            | ○               | ◐              | ◐             | 4     |
| Packages                      | ◐            | ●               | ◐              | ○             | 4     |
| Correctness                   | ○            | ●               | ○              | ○             | 2     |


The ranking in the strategy document deliberately does not follow the
scores: dependency and the competitive clock outrank them, which is why
the highest score is not ranked first.

## Deferred slices

Each item below is a later slice of a 90-day theme — deliberately not in
the first quarter, with the reason and the trigger that pulls it forward.

### Scope

**Role inheritance from the identity provider.**
Why not now: inherits onto roles v1, which must exist first; shaped with
early enterprise partners.
Trigger: roles v1 live and exercised by at least one partner.

**Sandbox identities for development.**
Why not now: user verification binds every user id to a real account —
correct for production, and it means simulating multiple users requires
real accounts today (this build created one per persona).
Trigger: enterprise pilots stalling on multi-user simulation.

**Identity per action class** (routine actions signed by a bot identity,
consequential ones by the person).
Why not now: delegation-as-the-user is the shipped half and it works;
first-class agent identity is a design chapter of its own.
Trigger: customers asking to distinguish agent posts from human posts in
their systems of record.

### Approval & Rules

**No-code rule builder GA.**
Why not now: the enforcement pipeline exists (hooks at four stages), but
rule authoring today means hosting your own service. MVP is sequenced
behind Scope, because rules over coarse identities enforce the wrong
thing.
Trigger: MVP validated with design partners.

**End-user limits** ("never let my agent do X").
Why not now: no surface exists for it today; belongs to the same rule
model as the builder.
Trigger: rule model v1 shipped.

### First-connection & legibility

**Provider-permission detection (the fourth fence).**
Why not now: distinguishing "user hasn't consented" from "user's provider
permissions can't cover this" requires querying the provider about the
user — a deeper integration per provider. The first three fences are
knowable from data the platform already holds.
Trigger: typed refusals shipped and the fourth-fence gap showing up in
support volume.

**Cross-surface consistency of the auth moment.**
Why not now: today the same authorization renders three ways (playground
re-sends the message; SDK prints a link and waits; desktop clients show a
connect card). Typed refusals define the vocabulary first.
Trigger: typed refusals shipped.

### Correctness

**Full pre-flight report** ("for this user, which of this agent's tools
will actually work?").
Why not now: a complete answer needs Scope's user model; a
configuration-time report against current grants ships first.
Trigger: Scope v1 live.

### Receipts

**Audit export GA.**
Why not now: surfacing the record in the product comes first; export
hardens after one customer security system consumes it in practice.
Trigger: first successful export integration.

### Judgment layer

**First-party detection** (catching behavior that looks wrong though no
rule forbids it).
Why not now: the deterministic layer is not built yet, and detection
without it underperforms what specialist partners already sell. The
posture for year one: open the hooks as a real product, integrate
partners.
Trigger: reviewed at month 12 against three tripwires — customers routing
external verdicts through the hooks; per-call blocking becoming what they
pay for; a partner attempting to become the control brand on top.