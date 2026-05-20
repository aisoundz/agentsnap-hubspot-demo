"""Smoke test for the AgentSnap HubSpot demo.

Exercises all 9 MCP tools end-to-end against the mock backend, matching the
8-prompt demo flow in the README. Prints each step's response so you can see
exactly what Claude would see.

Run:
    python smoke_test.py

What it verifies:
  - All tool implementations execute without exceptions
  - Seed data is internally consistent (named contacts exist, IDs cross-ref)
  - Spend cap fires on the big Hartford renewal ($7,820 > $5,000)
  - confirm_action successfully executes the held action
  - HubSpot side-effects (deal create + timeline note) land in runtime state
  - Audit log is written
  - All responses include the next_action LLM hint
"""

from __future__ import annotations

import json
import sys
from typing import Any, Callable

# Avoid needing the mcp SDK installed for the smoke test.
# Provide a tiny stub that captures registered tools.


class FakeMCP:
    """Minimal stand-in for FastMCP. Captures tools so the test can call them."""

    def __init__(self) -> None:
        self.tools: dict[str, Callable[..., Any]] = {}

    def tool(self, *args, **kwargs):
        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            self.tools[fn.__name__] = fn
            return fn

        return decorator


# ----------------------------------------------------------------------------
# Test runner helpers
# ----------------------------------------------------------------------------

PASS = "\033[32m✓\033[0m"
FAIL = "\033[31m✗\033[0m"
ARROW = "\033[36m→\033[0m"
DIM = "\033[2m"
RESET = "\033[0m"

_failures: list[str] = []


def section(title: str) -> None:
    print()
    print(f"\033[1m{title}\033[0m")
    print("─" * len(title))


def step(label: str) -> None:
    print(f"\n{ARROW} {label}")


def check(condition: bool, description: str) -> None:
    if condition:
        print(f"   {PASS} {description}")
    else:
        print(f"   {FAIL} {description}")
        _failures.append(description)


def show(payload: Any, max_lines: int = 12) -> None:
    text = json.dumps(payload, indent=2, default=str)
    lines = text.split("\n")
    if len(lines) > max_lines:
        head = "\n".join(lines[: max_lines - 1])
        print(f"{DIM}{head}\n   ... ({len(lines) - max_lines + 1} more lines){RESET}")
    else:
        print(f"{DIM}{text}{RESET}")


# ----------------------------------------------------------------------------
# Register tools against the FakeMCP
# ----------------------------------------------------------------------------

from tools import register_tools  # noqa: E402

mcp = FakeMCP()
register_tools(mcp)

# Sanity: exactly the 9 tools we expect
EXPECTED_TOOLS = {
    "get_daily_briefing",
    "get_renewal_pipeline",
    "search_contact",
    "get_contact_full",
    "create_renewal_invoice",
    "confirm_action",
    "create_claim",
    "list_claims",
    "get_commission_status",
}

section("Tool registration")
check(set(mcp.tools.keys()) == EXPECTED_TOOLS,
      f"9 tools registered ({len(mcp.tools)} found, set matches expected)")
if set(mcp.tools.keys()) != EXPECTED_TOOLS:
    missing = EXPECTED_TOOLS - set(mcp.tools.keys())
    extra = set(mcp.tools.keys()) - EXPECTED_TOOLS
    print(f"   Missing: {missing}")
    print(f"   Unexpected: {extra}")


def call(tool_name: str, **kwargs: Any) -> dict[str, Any]:
    return mcp.tools[tool_name](**kwargs)


# ----------------------------------------------------------------------------
# Demo flow — 8 prompts, plus list_claims as bonus
# ----------------------------------------------------------------------------

section("Demo flow — exercising every tool")

# 1. Daily briefing
step("Prompt: \"What's on my plate today?\"")
result = call("get_daily_briefing")
show(result)
check(result["urgent_renewals_count"] >= 1, "urgent_renewals_count >= 1")
check(result["overdue_invoices_count"] >= 1, "overdue_invoices_count >= 1")
check(result["open_claims_count"] >= 1, "open_claims_count >= 1")
check("next_action" in result, "next_action hint present")
check(result["mode"] == "mock", "running in mock mode")

# 2. Renewal pipeline
step("Prompt: \"Show me everyone whose policy expires in the next 30 days.\"")
result = call("get_renewal_pipeline", days=30)
show(result)
check(result["total"] >= 1, "at least 1 renewal in the next 30 days")
check(result["items"][0]["expires_in_days"] <= result["items"][-1]["expires_in_days"]
      if len(result["items"]) > 1 else True, "items sorted by expires_in_days ascending")
check(any(i["urgency"] == "urgent" for i in result["items"]), "at least one urgent item")

# 3. Search contact
step("Prompt: \"Look up Robert Martinez.\"")
result = call("search_contact", query="Robert Martinez")
show(result)
check(result["count"] >= 1, "at least 1 match for Robert Martinez")
robert = next((m for m in result["matches"] if "Robert" in m["name"]), None)
check(robert is not None, "Robert Martinez specifically in matches")

# 4. Full contact profile
step(f"Prompt: \"Pull Robert's full profile.\" (contact_id={robert['contact_id']})")
result = call("get_contact_full", contact_id=robert["contact_id"])
show(result)
check(result["name"] == "Robert Martinez", "name resolved to Robert Martinez")
check(result["policy"]["carrier"] == "Hartford", "policy carrier = Hartford")
check(result["policy"]["premium"] == 7820.00, "policy premium = $7,820 (will trip the cap)")

# 5. Renew Sarah Johnson — under the cap, should execute directly
step("Prompt: \"Renew Sarah Johnson's policy.\"")
sarah_search = call("search_contact", query="Sarah Johnson")
sarah = sarah_search["matches"][0]
result = call("create_renewal_invoice", contact_id=sarah["contact_id"])
show(result)
check(result.get("status") == "created", "invoice created directly (under cap)")
check("invoice" in result, "invoice payload returned")
check("hubspot_deal_id" in result, "HubSpot deal id returned (sync confirmed)")
check(result.get("hubspot_timeline_note") == "logged", "timeline note logged")

# 6. Renew Robert Martinez — over the cap, should ask for confirmation
step("Prompt: \"Renew Robert Martinez's Hartford policy.\" (expecting spend-cap hold)")
result = call("create_renewal_invoice", contact_id=robert["contact_id"])
show(result)
check(result.get("status") == "awaiting_confirmation",
      "spend cap fired — awaiting_confirmation status")
check("confirmation_id" in result, "confirmation_id returned for user to confirm")
check(result.get("amount") == 7820.00, "amount = $7,820")
check("preview" in result, "preview block tells the user who/what before confirming")
confirmation_id = result["confirmation_id"]

# 7. Confirm the held action
step(f"Prompt: \"Yes, confirm.\" (confirmation_id={confirmation_id[:16]}...)")
result = call("confirm_action", confirmation_id=confirmation_id)
show(result)
check(result.get("status") == "confirmed", "confirmation executed")
check("result" in result and "invoice" in result["result"], "invoice created on confirm")
check("hubspot_deal" in result["result"], "HubSpot deal created on confirm")

# 8. Open a property claim for Mike Chen
step("Prompt: \"Open a property claim for Mike Chen — water damage.\"")
mike_search = call("search_contact", query="Mike Chen")
mike = mike_search["matches"][0]
result = call("create_claim",
              contact_id=mike["contact_id"],
              claim_type="property",
              description="Water damage to the basement, suspected slow leak.")
show(result)
check(result.get("status") == "created", "claim created")
check(result["claim"]["claim_type"] == "property", "claim_type = property")
check(result["claim"]["id"].startswith("CL-2026-"), "claim id follows expected pattern")
check(result.get("hubspot_timeline_note") == "logged", "timeline note logged for the claim")

# 8b. Bonus — list all claims to confirm the new one is there
step("Bonus: \"Show me all open claims.\"")
result = call("list_claims")
show(result)
check(result["count"] >= 5, "claim count includes seed + new ones")
property_claim_found = any(c["description"].startswith("Water damage") for c in result["claims"])
check(property_claim_found, "the new Mike Chen claim appears in list_claims")

# 9. Commission status
step("Prompt: \"How much commission did I earn this quarter?\"")
result = call("get_commission_status")
show(result)
check(result["ytd_total"] > 0, "ytd_total > 0")
check(len(result["by_carrier"]) >= 1, "at least one carrier breakdown")
check("by_quarter" in result, "quarterly breakdown present")

# ----------------------------------------------------------------------------
# Side-effect verification — HubSpot runtime state should reflect the writes
# ----------------------------------------------------------------------------

section("HubSpot side-effect verification (mock runtime state)")

import seed_data  # noqa: E402

check(len(seed_data.RUNTIME_HUBSPOT_DEALS) >= 2,
      f"≥2 HubSpot deals created (got {len(seed_data.RUNTIME_HUBSPOT_DEALS)})")
check(len(seed_data.RUNTIME_HUBSPOT_TIMELINE) >= 3,
      f"≥3 HubSpot timeline notes created (got {len(seed_data.RUNTIME_HUBSPOT_TIMELINE)})")
check(len(seed_data.RUNTIME_INVOICES) >= 2,
      f"≥2 invoices created (got {len(seed_data.RUNTIME_INVOICES)})")
check(len(seed_data.RUNTIME_CLAIMS) >= 1,
      f"≥1 claim created (got {len(seed_data.RUNTIME_CLAIMS)})")

# ----------------------------------------------------------------------------
# Audit log verification
# ----------------------------------------------------------------------------

section("Audit log verification")

from pathlib import Path  # noqa: E402

audit_path = Path(__file__).parent / "audit_log.jsonl"
if audit_path.exists():
    lines = [ln for ln in audit_path.read_text().splitlines() if ln.strip()]
    check(len(lines) >= 4, f"≥4 audit log entries (got {len(lines)})")
    for ln in lines[-5:]:
        try:
            event = json.loads(ln)
            print(f"   {DIM}{event.get('action'):>30}  {event.get('timestamp', '')[:19]}{RESET}")
        except Exception:
            print(f"   {DIM}(bad line: {ln[:60]}){RESET}")
else:
    check(False, "audit_log.jsonl was created")

# ----------------------------------------------------------------------------
# Final result
# ----------------------------------------------------------------------------

section("Result")
if _failures:
    print(f"{FAIL} {len(_failures)} check(s) failed:")
    for f in _failures:
        print(f"   - {f}")
    sys.exit(1)
else:
    print(f"{PASS} All smoke checks passed.")
    print()
    print("The demo is ready to send to CJ. Run it through Claude Desktop")
    print("for a final visual check before hitting send.")
    sys.exit(0)
