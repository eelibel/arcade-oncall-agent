#!/usr/bin/env python3
"""Incident-triage agent for Meridian Mutual's AI Platform Team.

Pipeline entry point: in production a GitHub webhook fires this when an issue
is filed; here it is started manually with one command:

    python agent/triage_agent.py <issue_number>

The agent reads the issue, mines past incidents (closed ones included),
inspects recent repository activity for suspect commits, checks who is on
call and what claims are impacted, then drafts a Slack update for #incidents
and a GitHub comment. NOTHING is written anywhere until a human approves at
the single gate: the agent proposes, the human approves, then actions execute.

Anthropic (claude-sonnet-4-6) is the reasoning brain; every tool call runs
through Arcade under the on-call engineer's identity.
"""

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

ARCADE_USER_ID = "elisa.bellagamba@gmail.com"
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


# --- Stubs (integrations pending) ---------------------------------------------


def get_oncall():
    # TODO: replace with Arcade Pagerduty.ListOncalls once the PagerDuty
    # connection is live.
    return "Priya Raman (on call until 6pm, then Marco Silva)"


def get_claim_impact():
    # TODO: replace with a ClaimsCore custom-toolkit call (claim status by ID)
    # once the toolkit is wired into Arcade.
    return "1 claim delayed — intake-validation bug; the fix is in this blocked deploy"


# --- Flow ---------------------------------------------------------------------


def main():
    if len(sys.argv) != 2 or not sys.argv[1].isdigit():
        print("Usage: python agent/triage_agent.py <issue_number>")
        sys.exit(1)
    issue_number = int(sys.argv[1])
    repo = {"owner": REPO_OWNER, "repo": REPO_NAME}

    print(f"[1/9] Triage started for {REPO_OWNER}/{REPO_NAME}#{issue_number}")

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
        "the single closest past incident."
    )
    print("      --- Similar-incident ranking ---")
    print(similar_analysis)

    # 4. Recent repository activity — suspect commits.
    print("[4/9] Pulling recent activity via Github.ListRepositoryActivities ...")
    activity = execute_tool(
        "Github.ListRepositoryActivities", {**repo, "per_page": 30, "direction": "desc"}
    )
    print("      Flagging suspect commits with the model ...")
    commit_reply = ask_model(
        "New incident:\n\n"
        f"{compact(issue)}\n\n"
        "Recent repository activity (pushes, branches, actors):\n\n"
        f"{compact(activity)}\n\n"
        "Flag any commit or push that plausibly relates to the symptom, with "
        "a short reason each; say so plainly if none do. Then reply with a "
        "JSON object on its own line at the end: "
        '{"files_to_inspect": ["path", ...]} listing up to 2 repository file '
        "paths whose contents would help confirm a suspect (empty list if none)."
    )
    print("      --- Suspect-commit analysis ---")
    print(commit_reply)

    file_excerpts = {}
    try:
        for path in extract_json(commit_reply).get("files_to_inspect", [])[:2]:
            print(f"      Inspecting {path} via Github.GetFileContents ...")
            try:
                file_excerpts[path] = execute_tool(
                    "Github.GetFileContents", {**repo, "path": path}
                )
            except RuntimeError as err:
                file_excerpts[path] = f"(fetch failed: {err})"
    except (ValueError, json.JSONDecodeError):
        pass  # no inspectable files named; proceed without excerpts

    # 5. On-call lookup (stub).
    print("[5/9] Looking up on-call rotation (stub — PagerDuty pending) ...")
    oncall = get_oncall()
    print(f"      On call: {oncall}")

    # 6. Claim-impact check (stub).
    print("[6/9] Checking claim impact (stub — ClaimsCore toolkit pending) ...")
    claim_impact = get_claim_impact()
    print(f"      Impact: {claim_impact}")

    # 7. Compose the drafts.
    print("[7/9] Composing the #incidents draft and issue comment ...")
    compose_reply = ask_model(
        "Compose the incident-triage output from this assembled context.\n\n"
        f"TRIGGERING ISSUE (#{issue_number}):\n{compact(issue)}\n\n"
        f"SIMILAR PAST INCIDENTS (ranked):\n{similar_analysis}\n\n"
        f"SUSPECT COMMITS:\n{commit_reply}\n\n"
        f"INSPECTED FILES:\n{compact(file_excerpts, 6000)}\n\n"
        f"ON CALL: {oncall}\n\n"
        f"CLAIM IMPACT: {claim_impact}\n\n"
        "Return ONLY a JSON object with two string fields:\n"
        '- "slack_message": the update for #incidents, containing in order: '
        "incident summary; probable cause with the suspect commit reference; "
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

    if answer != "y":
        # 10. Declined: exit without writing anything.
        print("[9/9] Not approved. Exiting without posting or logging.")
        sys.exit(0)

    # 9. Approved: execute both writes, then log the approval event.
    print(f"[9/9] Approved. Posting to #{SLACK_CHANNEL} via Slack.SendMessage ...")
    execute_tool(
        "Slack.SendMessage", {"channel_name": SLACK_CHANNEL, "message": slack_draft}
    )
    print("      Slack message sent.")

    print("      Commenting on the issue via Github.CreateIssueComment ...")
    execute_tool(
        "Github.CreateIssueComment",
        {**repo, "issue_number": issue_number, "body": comment_draft},
    )
    print("      Issue comment posted.")

    # The hash proves exactly what was approved; the text keeps it readable.
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "approver": ARCADE_USER_ID,
        "draft_sha256": hashlib.sha256(draft_text.encode("utf-8")).hexdigest(),
        "draft_text": draft_text,
    }
    with open(APPROVALS_LOG, "a", encoding="utf-8") as log:
        log.write(json.dumps(record) + "\n")
    print(f"      Approval logged to {APPROVALS_LOG.name}.")
    print("Done.")


if __name__ == "__main__":
    main()
