#!/usr/bin/env python3
"""ClaimsCore — Meridian Mutual's (fictional) internal claims system.

There is no separate API server: these tools ARE the system, backed by a
small hard-coded dataset. In Meridian's production posture this would be a
thin wrapper over the real ClaimsCore API, deployed inside their VPC; the
architecture (custom tools registered with Arcade, per-user attribution,
secret-gated access) is identical either way.

Both tools require the CLAIMSCORE_API_TOKEN secret — simulating the internal
API credential — and refuse to run without it. The secret is configured in
Arcade (uploaded from .env at deploy time), never visible to the LLM.
"""

import sys
from typing import Annotated

from arcade_mcp_server import Context, MCPApp
from arcade_mcp_server.exceptions import ToolExecutionError

app = MCPApp(name="claimscore", version="1.0.0")

# --- Dataset: group-benefits claims for Meridian's clients ---------------------

CLAIMS = {
    "CLM-2214": {
        "claim_id": "CLM-2214",
        "policyholder": "Hartwell Manufacturing",
        "policy_number": "GB-88121",
        "type": "group short-term disability",
        "amount_usd": 18400,
        "filed": "2026-08-03",
        "status": "delayed — intake validation error; fix pending deploy",
        "note": "Claim intake failed schema validation; hotfix is in the blocked claims-service deploy.",
    },
    "CLM-2201": {
        "claim_id": "CLM-2201",
        "policyholder": "Ridgeline Logistics",
        "policy_number": "GB-77410",
        "type": "group dental",
        "amount_usd": 2150,
        "filed": "2026-08-01",
        "status": "in review",
        "note": "Standard review; no action needed.",
    },
    "CLM-2188": {
        "claim_id": "CLM-2188",
        "policyholder": "Bexley Health Group",
        "policy_number": "GB-90233",
        "type": "group life",
        "amount_usd": 250000,
        "filed": "2026-07-28",
        "status": "approved",
        "note": "Approved; disbursement scheduled.",
    },
    "CLM-2169": {
        "claim_id": "CLM-2169",
        "policyholder": "Cascade Textiles",
        "policy_number": "GB-55192",
        "type": "group vision",
        "amount_usd": 640,
        "filed": "2026-07-21",
        "status": "paid",
        "note": "Paid 2026-07-30.",
    },
    "CLM-2222": {
        "claim_id": "CLM-2222",
        "policyholder": "Northgate Foods",
        "policy_number": "GB-61077",
        "type": "group long-term disability",
        "amount_usd": 51200,
        "filed": "2026-08-07",
        "status": "received",
        "note": "Awaiting intake processing.",
    },
    "CLM-2197": {
        "claim_id": "CLM-2197",
        "policyholder": "Iron Peak Outfitters",
        "policy_number": "GB-43850",
        "type": "group dental",
        "amount_usd": 3980,
        "filed": "2026-07-30",
        "status": "in review",
        "note": "Additional documentation requested.",
    },
}

COVERAGE = {
    "GB-88121": {
        "policy_number": "GB-88121",
        "policyholder": "Hartwell Manufacturing",
        "plan": "Group Benefits — Premier",
        "lines": ["short-term disability", "long-term disability", "dental", "vision"],
        "covered_lives": 812,
        "effective": "2025-01-01",
        "renewal": "2026-12-31",
        "status": "active",
    },
    "GB-77410": {
        "policy_number": "GB-77410",
        "policyholder": "Ridgeline Logistics",
        "plan": "Group Benefits — Standard",
        "lines": ["dental", "vision"],
        "covered_lives": 340,
        "effective": "2025-06-01",
        "renewal": "2026-05-31",
        "status": "active",
    },
    "GB-90233": {
        "policy_number": "GB-90233",
        "policyholder": "Bexley Health Group",
        "plan": "Group Benefits — Premier",
        "lines": ["life", "short-term disability", "dental"],
        "covered_lives": 1275,
        "effective": "2024-09-01",
        "renewal": "2026-08-31",
        "status": "active",
    },
    "GB-55192": {
        "policy_number": "GB-55192",
        "policyholder": "Cascade Textiles",
        "plan": "Group Benefits — Standard",
        "lines": ["vision", "dental"],
        "covered_lives": 205,
        "effective": "2025-03-01",
        "renewal": "2027-02-28",
        "status": "active",
    },
    "GB-61077": {
        "policy_number": "GB-61077",
        "policyholder": "Northgate Foods",
        "plan": "Group Benefits — Premier",
        "lines": ["long-term disability", "life"],
        "covered_lives": 990,
        "effective": "2025-11-01",
        "renewal": "2026-10-31",
        "status": "active",
    },
    "GB-43850": {
        "policy_number": "GB-43850",
        "policyholder": "Iron Peak Outfitters",
        "plan": "Group Benefits — Standard",
        "lines": ["dental"],
        "covered_lives": 88,
        "effective": "2026-01-01",
        "renewal": "2026-12-31",
        "status": "active",
    },
}


def _require_token(context: Context) -> None:
    """Simulate the internal API credential check: no token, no data."""
    try:
        token = context.get_secret("CLAIMSCORE_API_TOKEN")
    except Exception:
        token = None
    if not token:
        raise ToolExecutionError(
            "ClaimsCore API token not configured (secret CLAIMSCORE_API_TOKEN)."
        )


@app.tool(requires_secrets=["CLAIMSCORE_API_TOKEN"])
def get_claim_status(
    context: Context,
    claim_id: Annotated[str, "ClaimsCore claim ID, e.g. 'CLM-2214'"],
) -> Annotated[dict, "The claim's status record"]:
    """Get the status record for a claim by its ClaimsCore claim ID."""
    _require_token(context)
    claim = CLAIMS.get(claim_id.strip().upper())
    if claim is None:
        raise ToolExecutionError(
            f"No claim found with ID '{claim_id}'. Known IDs look like 'CLM-2214'."
        )
    return claim


@app.tool(requires_secrets=["CLAIMSCORE_API_TOKEN"])
def check_coverage(
    context: Context,
    policy_number: Annotated[str, "Group-benefits policy number, e.g. 'GB-88121'"],
) -> Annotated[dict, "The policy's coverage record"]:
    """Get the coverage record for a group-benefits policy by policy number."""
    _require_token(context)
    coverage = COVERAGE.get(policy_number.strip().upper())
    if coverage is None:
        raise ToolExecutionError(
            f"No policy found with number '{policy_number}'. "
            "Known policy numbers look like 'GB-88121'."
        )
    return coverage


if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    app.run(transport=transport, host="127.0.0.1", port=8000)
