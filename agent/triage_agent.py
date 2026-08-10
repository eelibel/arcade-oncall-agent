#!/usr/bin/env python3
"""Incident-triage agent for Meridian Mutual's AI Platform Team.

Pipeline entry point: in production a GitHub webhook fires this when an issue
is filed; here it is started manually with one command:

    python agent/triage_agent.py <issue_number> [--user <arcade_user_id>]

The agent reads the issue, mines past incidents (closed ones included),
inspects the current deploy/runner configuration for likely regressions
(the GitHub toolkit has no repo-level commit listing, so cause analysis
works from current config state plus incident history), checks who is on
call and what claims are impacted, then drafts a Slack update for #incidents
and a GitHub comment. NOTHING is written anywhere until a human approves at
the single gate: the agent proposes, the human approves, then actions execute.

Anthropic (claude-sonnet-4-6) is the reasoning brain; every tool call runs
through Arcade under the on-call engineer's identity.
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from anthropic import Anthropic
from arcadepy import Arcade
from dotenv import load_dotenv

# --- Configuration -----------------------------------------------------------

load_dotenv()  # .env at the repo root

# Must be a real Arcade account: persona user_ids fail Arcade's user
# verification. Overridable via the --user flag.
DEFAULT_USER_ID = "elisa.bellagamba@gmail.com"
ARCADE_USER_ID = DEFAULT_USER_ID
REPO_OWNER = "eelibel"
REPO_NAME = "meridian-platform"
SLACK_CHANNEL = "incidents"
MODEL = "claude-sonnet-4-6"
APPROVALS_LOG = Path(__file__).resolve().parent.parent / "approvals.log"

arcade = Arcade(api_key=os.environ["ARCADE_API_KEY"])
claude = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# --- Helpers -----------------------------------------------------------------


def execute_tool(tool_name, tool_input):
    """Authorize (just-in-time) and execute one Arcade tool call.

    Authorization is per-tool and per-user: a user who lacks a grant is
    stopped here, at the step that needs it, not earlier.
    """
    auth = arcade.tools.authorize(tool_name=tool_name, user_id=ARCADE_USER_ID)
    if auth.status != "completed":
        print(f"    Authorization required for {tool_name}.")
        print(f"    Visit: {auth.url}")
        arcade.auth.wait_for_completion(auth)
        print("    Authorization completed.")

    response = arcade.tools.execute(
        tool_name=tool_name, input=tool_input, user_id=ARCADE_USER_ID
    )
    if response.output is not None and response.output.error is not None:
        raise RuntimeError(f"{tool_name} failed: {response.output.error}")
    return response.output.value


def ask_model(prompt, max_tokens=2000):
    """One reasoning call to Claude; returns the text of the reply."""
    message = claude.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=(
            "You are an incident-triage analyst for Meridian Mutual's AI "
            "Platform Team. Be precise, cite issue/commit identifiers, and "
            "never invent facts that are not in the data you are given."
        ),
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def extract_json(text):
    """Parse a JSON object out of a model reply (tolerates code fences)."""
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else text[text.find("{"): text.rfind("}") + 1]
    return json.loads(candidate)


def compact(data, limit=12000):
    """JSON-serialize tool output, truncated so prompts stay bounded."""
    text = json.dumps(data, default=str)
    return text if len(text) <= limit else text[:limit] + " ...[truncated]"


def log_event(record):
    """Append one timestamped JSON line to the audit log."""
    record = {"timestamp": datetime.now(timezone.utc).isoformat(), **record}
    with open(APPROVALS_LOG, "a", encoding="utf-8") as log:
        log.write(json.dumps(record) + "\n")


# --- Lookups (on-call still stubbed; PagerDuty pending) ------------------------


def get_oncall():
    # TODO: replace with Arcade Pagerduty.ListOncalls once the PagerDuty
    # connection is live.
    return "Priya Raman (on call until 6pm, then Marco Silva)"


def get_claim_impact():
    """Check claim impact via the ClaimsCore custom toolkit (real Arcade call)."""
    # SIMPLIFICATION: claim selection is hard-coded; a real pipeline would map
    # the affected service to its impacted claims.
    claim = execute_tool("Claimscore.GetClaimStatus", {"claim_id": "CLM-2214"})
    return (
        f"Claim {claim['claim_id']} ({claim['policyholder']}): {claim['status']}"
        if isinstance(claim, dict)
        else str(claim)
    )


# --- Flow ---------------------------------------------------------------------


def main():
    global ARCADE_USER_ID
    parser = argparse.ArgumentParser(description="Incident-triage agent")
    parser.add_argument("issue_number", type=int, help="GitHub issue number to triage")
    parser.add_argument(
        "--user",
        default=DEFAULT_USER_ID,
        help=f"Arcade user_id to run as (default: {DEFAULT_USER_ID})",
    )
    args = parser.parse_args()
    issue_number = args.issue_number
    ARCADE_USER_ID = args.user
    repo = {"owner": REPO_OWNER, "repo": REPO_NAME}

    print(
        f"[1/9] Triage started for {REPO_OWNER}/{REPO_NAME}#{issue_number} "
        f"as {ARCADE_USER_ID}"
    )

    # 2. Fetch the triggering issue.
    print("[2/9] Fetching the issue via Github.GetIssue ...")
    issue = execute_tool("Github.GetIssue", {**repo, "issue_number": issue_number})
    issue_title = issue.get("title", "(no title)") if isinstance(issue, dict) else str(issue)
    print(f"      Issue: {issue_title}")

    # 3. Search past incidents — open AND closed; closed is where resolved
    #    history lives.
    print('[3/9] Searching past incidents via Github.ListIssues (state="all") ...')
    all_issues = execute_tool(
        "Github.ListIssues",
        {**repo, "state": "all", "sort": "updated", "direction": "desc", "per_page": 50},
    )
    print("      Ranking similar incidents with the model ...")
    similar_analysis = ask_model(
        "A new incident was just filed:\n\n"
        f"{compact(issue)}\n\n"
        "Here are past issues from the same repository, open and closed "
        "(closed ones contain resolution history):\n\n"
        f"{compact(all_issues)}\n\n"
        f"Excluding issue #{issue_number} itself, rank the most similar past "
        "incidents by relevance to the new one. For each, give the issue "
        "number, title, state, a one-line reason for its rank, and — if it "
        "was closed — how it appears to have been resolved. Finish by naming "
        "the single closest past incident, then reply with a JSON object on "
        'its own line at the end: {"closest_issue_number": <number>}.'
    )
    print("      --- Similar-incident ranking ---")
    print(similar_analysis)

    # The toolkit can WRITE issue comments (CreateIssueComment) but has no
    # tool to READ them, so the resolution discussion in a closed issue's
    # comments is unreachable; the issue body verbatim is the best available.
    closest_issue = None
    closest_number = None
    try:
        closest_number = int(extract_json(similar_analysis)["closest_issue_number"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        print("      (could not identify a closest past incident; continuing)")
    if closest_number is not None and closest_number != issue_number:
        print(
            "      note: issue-comment reading unavailable in toolkit — "
            "resolution comments on the closest incident are unreachable; "
            "using its issue body verbatim"
        )
        print(f"      Fetching closest incident #{closest_number} via Github.GetIssue ...")
        closest_issue = execute_tool(
            "Github.GetIssue", {**repo, "issue_number": closest_number}
        )

    # 4. Probable-cause analysis from current config state.
    #    The GitHub toolkit exposes no repo-level commit listing
    #    (ListRepositoryActivities returns only event IDs and actors, and
    #    ListPullRequestCommits is per-PR), so instead of commit archaeology
    #    the agent reads the current deploy/runner config and reasons about
    #    likely regressions from current state + incident history.
    print("[4/9] Analyzing current config state for likely regressions ...")
    print(
        "      note: repo-level commit listing unavailable in toolkit — "
        "inferring from current config state"
    )
    # SIMPLIFICATION: config paths are known here; a real deployment would
    # walk the repo tree.
    config_paths = [
        "infra/runners/autoscale.yaml",
        "infra/pipelines/group-benefits-deploy.yaml",
    ]
    config_files = {}
    for path in config_paths:
        print(f"      Fetching {path} via Github.GetFileContents ...")
        try:
            config_files[path] = execute_tool(
                "Github.GetFileContents", {**repo, "path": path}
            )
        except RuntimeError as err:
            config_files[path] = f"(fetch failed: {err})"

    print("      Reasoning about likely regressions with the model ...")
    cause_analysis = ask_model(
        "New incident:\n\n"
        f"{compact(issue)}\n\n"
        "Current contents of the deploy/runner configuration files:\n\n"
        f"{compact(config_files)}\n\n"
        "Summaries of similar past incidents and their resolutions:\n\n"
        f"{similar_analysis}\n\n"
        "Closest past incident, body verbatim (its resolution comments are "
        "not readable through the toolkit, so this is the fullest available "
        "record of how it was resolved):\n\n"
        f"{compact(closest_issue) if closest_issue else '(none identified)'}\n\n"
        "Reason about the likely regression: which current config values or "
        "recent-looking changes plausibly explain the symptom, especially "
        "where the past incidents suggest what a healthy state looked like? "
        "Name the specific file and setting for each suspect, with a short "
        "reason; say so plainly if the configs look unrelated to the symptom."
    )
    print("      --- Probable-cause analysis ---")
    print(cause_analysis)

    # 5. On-call lookup (stub).
    print("[5/9] Looking up on-call rotation (stub — PagerDuty pending) ...")
    oncall = get_oncall()
    print(f"      On call: {oncall}")

    # 6. Claim-impact check via ClaimsCore.
    print("[6/9] Checking claim impact via Claimscore.GetClaimStatus ...")
    claim_impact = get_claim_impact()
    print(f"      Impact: {claim_impact}")

    # 7. Compose the drafts.
    print("[7/9] Composing the #incidents draft and issue comment ...")
    compose_reply = ask_model(
        "Compose the incident-triage output from this assembled context.\n\n"
        f"TRIGGERING ISSUE (#{issue_number}):\n{compact(issue)}\n\n"
        f"SIMILAR PAST INCIDENTS (ranked):\n{similar_analysis}\n\n"
        f"PROBABLE-CAUSE ANALYSIS (from current config state):\n{cause_analysis}\n\n"
        f"CURRENT CONFIG FILES:\n{compact(config_files, 6000)}\n\n"
        f"ON CALL: {oncall}\n\n"
        f"CLAIM IMPACT: {claim_impact}\n\n"
        "Return ONLY a JSON object with two string fields:\n"
        '- "slack_message": the update for #incidents, containing in order: '
        "incident summary; probable cause naming the implicated config file "
        "and setting (or commit, if one is identifiable from history); "
        "closest past incident and how it was resolved; one business-impact "
        "line from the claim data; suggested page (the on-call person). "
        "Plain text with short labeled lines, no markdown headers.\n"
        '- "github_comment": a comment for issue '
        f"#{issue_number} linking the closest past incident (as #<number>) "
        "and stating how it was resolved, so the assignee has the history "
        "in-thread.\n"
    )
    drafts = extract_json(compose_reply)
    slack_draft = drafts["slack_message"].strip()
    comment_draft = drafts["github_comment"].strip()

    # 8. HARD STOP — the approval gate. Nothing executes before the answer.
    draft_text = (
        f"=== DRAFT 1: Slack message -> #{SLACK_CHANNEL} ===\n"
        f"{slack_draft}\n\n"
        f"=== DRAFT 2: GitHub comment -> {REPO_OWNER}/{REPO_NAME}#{issue_number} ===\n"
        f"{comment_draft}"
    )
    print("\n[8/9] APPROVAL GATE " + "=" * 50)
    print(draft_text)
    print("=" * 69)
    answer = input("Post to #incidents and comment on the issue? (y/n) ").strip().lower()

    # The decision record: the hash proves exactly what was approved (or
    # declined); the text keeps it readable.
    decision_record = {
        "approver": ARCADE_USER_ID,
        "draft_sha256": hashlib.sha256(draft_text.encode("utf-8")).hexdigest(),
        "draft_text": draft_text,
    }

    if answer != "y":
        # 10. Declined: an audit event too — log it, execute nothing.
        log_event({**decision_record, "decision": "declined", "note": "nothing executed"})
        print(f"[9/9] Not approved. Decline logged to {APPROVALS_LOG.name}; nothing executed.")
        sys.exit(0)

    # 9. Approved: record the approval BEFORE any tool executes, so a crash
    #    mid-write can never lose the fact that approval was given.
    log_event({**decision_record, "decision": "approved"})
    print(f"[9/9] Approved. Approval logged to {APPROVALS_LOG.name}.")

    # Each write is attempted and its outcome logged independently: one
    # failing must not hide the outcome of the other.
    actions = [
        (
            "slack_post",
            f"Posting to #{SLACK_CHANNEL} via Slack.SendMessage ...",
            "Slack.SendMessage",
            {"channel_name": SLACK_CHANNEL, "message": slack_draft},
        ),
        (
            "github_comment",
            "Commenting on the issue via Github.CreateIssueComment ...",
            "Github.CreateIssueComment",
            {**repo, "issue_number": issue_number, "body": comment_draft},
        ),
    ]
    failures = 0
    for action, banner, tool_name, tool_input in actions:
        print(f"      {banner}")
        try:
            execute_tool(tool_name, tool_input)
            log_event({"action": action, "outcome": "sent"})
            print(f"      {action}: sent.")
        except Exception as err:
            failures += 1
            error_kind = f"{type(err).__name__}: {str(err)[:300]}"
            log_event({"action": action, "outcome": "failed", "error_kind": error_kind})
            print(f"      {action}: FAILED — {error_kind}")

    if failures:
        print(f"Done with {failures} failed action(s); see {APPROVALS_LOG.name}.")
        sys.exit(1)
    print("Done.")


if __name__ == "__main__":
    main()
