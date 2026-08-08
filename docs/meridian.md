# Meridian Mutual Insurance — the customer this build serves

Meridian Mutual is a fictional Fortune-2000 P&C and group-benefits insurer: ~$14B revenue, ~24,000 employees. Okta is the identity provider; security posture is customer-VPC / self-hosted for anything near claims or member data. An AI governance board and the CISO can each veto new systems.

After a CEO-level "AI-first operations" push, every business unit wants agents. The AI Platform Team — six people — runs the internal machinery (CI/CD, deployment platform, shared services) and fields those requests. Their twin fears: becoming the bottleneck, or becoming the headline. A platform engineer on this team leads technical validation of Arcade; the budget belongs to the CTO.

The validation strategy: dogfood on the platform team's own stack first, prove the control pattern, then extend the same governed path to business units. The control pattern — agent proposes, human approves, action executes — is the thing being validated; every future Meridian agent inherits it.

## Use case 1 — Incident triage (platform team, dogfood)

An engineer files a GitHub issue: CI runners are timing out and blocking the claims-service deploy — and that deploy carries the hotfix for a claims-intake bug already delaying a customer claim in production. The agent reads the issue, searches past issues for duplicates, pulls recent commits for suspects, asks PagerDuty who is on call, checks claim impact via ClaimsCore, and drafts a Slack message for #incidents: summary, probable cause, prior occurrence, business impact, suggested page. Hard stop — a human approves before anything posts. Automation solved notification years ago; the agent compresses interpretation (the 15–25 minutes of context assembly per incident).

## Use case 2 — Client servicing / meeting prep (business unit)

Amara, a group-benefits account manager, preps for a client renewal using an interactive agent over Calendar, Gmail, and Docs — and answers a live claims question mid-call. Same governed path as use case 1, different buyer mode: productivity agents for business users, reaching internal systems safely.

## ClaimsCore — the shared capability

Meridian's internal claims system, faked here as a small API (claim status by ID, coverage by policy number) and wired into Arcade once as a custom toolkit. Both use cases call it, and every call runs with the permissions of the person asking — the on-call engineer's impact check runs as her, Amara's client answer runs as Amara. No shared service account: the platform can always answer "who touched claims data, and when." For an insurer with a governance board, that per-person attribution is the point.

## Cast


| Person         | Role                                      | In this build                                                                                        |
| -------------- | ----------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| Priya Raman    | Senior platform engineer, primary on-call | Use case 1's actor and approver. Full grants: GitHub read+write, Slack post, PagerDuty read.         |
| Jordan Lee     | Junior platform engineer                  | Contrast case: GitHub read only, no Slack grant.                                                     |
| Marco Silva    | Platform engineer, secondary on-call      | Takes the pager at 6pm; appears in the PagerDuty rotation.                                           |
| Katherine Boyd | AI Platform Lead                          | Intended approver in the enterprise pattern; this build self-approves and names that simplification. |
| Amara Diallo   | Group-benefits account manager            | Use case 2's persona.                                                                                |


All personas are fictional. Two real test accounts run everything: the primary account plays Priya and Amara; the secondary plays Jordan. Marco and Katherine are names only.