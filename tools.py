"""MCP tools for the AgentSnap HubSpot demo.

9 tools wired to the demo flow:
  1. get_daily_briefing      — opening snapshot
  2. get_renewal_pipeline    — policies expiring in N days, sorted urgent first
  3. search_contact          — find a HubSpot contact by name/email/phone
  4. get_contact_full        — full profile: HubSpot data + policies + claims
  5. create_renewal_invoice  — write action; spend cap; syncs to HubSpot deal + timeline
  6. confirm_action          — execute a spend-cap-held action
  7. create_claim            — open a claim; logs to HubSpot timeline
  8. list_claims             — view claims with optional filters
  9. get_commission_status   — earnings by carrier + quarterly breakdown

Every tool returns a dict with a `next_action` field — a short hint to the
LLM about what to offer the user next. This is the AgentSnap pattern.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any

import config
import safety
from backends import AgentSnapClient, HubSpotClient

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


hubspot = HubSpotClient()
agentsnap = AgentSnapClient()


def register_tools(mcp: "FastMCP") -> None:
    """Register all demo tools on the provided FastMCP instance.

    Accepts anything that exposes a `tool()` decorator method — including a
    test stub — so the tools are exercisable without installing the mcp SDK.
    """

    # ----------------------------------------------------------------------
    # Tool 1 — Daily briefing
    # ----------------------------------------------------------------------

    @mcp.tool()
    def get_daily_briefing() -> dict[str, Any]:
        """Snapshot of today's priorities for the agent: urgent renewals,
        overdue invoices, open claims, and commission earned year-to-date.

        Use this as the opening prompt of a session — it answers "what should
        I work on today?" in one call.
        """
        urgent_renewals = hubspot.list_contacts_with_expiring_policies(days_ahead=14)
        overdue_invoices = agentsnap.list_invoices(status="overdue")
        open_claims = [
            c for c in agentsnap.list_claims()
            if c["status"] in ("open", "under_review", "investigating")
        ]
        commission = agentsnap.get_commission_summary()
        spend = safety.get_daily_spend()

        # Decorate renewals with carrier and premium for the LLM to summarize
        decorated_renewals = []
        for c in urgent_renewals:
            p = c["properties"]
            exp_iso = p.get("policy_expiration_date")
            try:
                days_left = (date.fromisoformat(exp_iso) - date.today()).days
            except Exception:
                days_left = None
            decorated_renewals.append({
                "contact_id": c["id"],
                "name": f"{p.get('firstname', '')} {p.get('lastname', '')}".strip(),
                "carrier": p.get("carrier"),
                "policy_type": p.get("policy_type"),
                "premium": float(p.get("policy_premium", 0) or 0),
                "expires_in_days": days_left,
                "policy_number": p.get("policy_number"),
            })

        return {
            "mode": config.HUBSPOT_MODE,
            "urgent_renewals_count": len(decorated_renewals),
            "urgent_renewals": decorated_renewals[:5],  # top 5
            "overdue_invoices_count": len(overdue_invoices),
            "open_claims_count": len(open_claims),
            "commission_ytd": commission["ytd_total"],
            "spend_today": spend["spent"],
            "spend_remaining_today": spend["remaining"],
            "next_action": (
                "Summarize the most urgent items for the user. Lead with the top "
                "renewal (smallest expires_in_days). Offer to advance one or to "
                "pull the full renewal pipeline with get_renewal_pipeline."
            ),
        }

    # ----------------------------------------------------------------------
    # Tool 2 — Renewal pipeline
    # ----------------------------------------------------------------------

    @mcp.tool()
    def get_renewal_pipeline(days: int = 30) -> dict[str, Any]:
        """Get policies expiring in the next N days. Default 30, max 365.

        Returns each contact with name, carrier, premium, expiration date,
        days until expiration, and an urgency tier (urgent / soon / upcoming).
        Sorted urgent first.
        """
        days = max(1, min(int(days), 365))
        contacts = hubspot.list_contacts_with_expiring_policies(days_ahead=days)

        items = []
        for c in contacts:
            p = c["properties"]
            exp_iso = p.get("policy_expiration_date")
            try:
                days_left = (date.fromisoformat(exp_iso) - date.today()).days
            except Exception:
                continue

            if days_left <= 14:
                urgency = "urgent"
            elif days_left <= 30:
                urgency = "soon"
            else:
                urgency = "upcoming"

            items.append({
                "contact_id": c["id"],
                "name": f"{p.get('firstname', '')} {p.get('lastname', '')}".strip(),
                "email": p.get("email"),
                "carrier": p.get("carrier"),
                "policy_type": p.get("policy_type"),
                "policy_number": p.get("policy_number"),
                "premium": float(p.get("policy_premium", 0) or 0),
                "expires_on": exp_iso,
                "expires_in_days": days_left,
                "urgency": urgency,
            })

        items.sort(key=lambda x: x["expires_in_days"])

        return {
            "window_days": days,
            "total": len(items),
            "items": items,
            "next_action": (
                "Show the user the urgent ones first. Offer to advance the top "
                "renewal with create_renewal_invoice."
            ),
        }

    # ----------------------------------------------------------------------
    # Tool 3 — Search contact
    # ----------------------------------------------------------------------

    @mcp.tool()
    def search_contact(query: str) -> dict[str, Any]:
        """Search HubSpot contacts by name, email, or phone. Returns up to 10
        matches with their basic identifying info.
        """
        results = hubspot.search_contacts(query=query, limit=10)
        decorated = [
            {
                "contact_id": r["id"],
                "name": f"{r['properties'].get('firstname', '')} {r['properties'].get('lastname', '')}".strip(),
                "email": r["properties"].get("email"),
                "phone": r["properties"].get("phone"),
                "carrier": r["properties"].get("carrier"),
                "policy_type": r["properties"].get("policy_type"),
            }
            for r in results
        ]
        return {
            "query": query,
            "count": len(decorated),
            "matches": decorated,
            "next_action": (
                "If exactly one match, offer to pull the full profile with "
                "get_contact_full. If multiple, ask the user to pick one."
            ),
        }

    # ----------------------------------------------------------------------
    # Tool 4 — Full contact profile
    # ----------------------------------------------------------------------

    @mcp.tool()
    def get_contact_full(contact_id: str) -> dict[str, Any]:
        """Pull a full contact profile: HubSpot data plus policies, invoices,
        and claims from AgentSnap.
        """
        contact = hubspot.get_contact(contact_id)
        if contact is None:
            return {"error": f"Contact {contact_id} not found"}

        p = contact["properties"]
        invoices = agentsnap.list_invoices(contact_id=contact_id)
        claims = agentsnap.list_claims(contact_id=contact_id)
        carrier_name = p.get("carrier")
        carrier = agentsnap.get_carrier_by_name(carrier_name) if carrier_name else None

        return {
            "contact_id": contact_id,
            "name": f"{p.get('firstname', '')} {p.get('lastname', '')}".strip(),
            "email": p.get("email"),
            "phone": p.get("phone"),
            "city": p.get("city"),
            "state": p.get("state"),
            "policy": {
                "type": p.get("policy_type"),
                "carrier": carrier_name,
                "carrier_commission_rate": carrier["commission_rate"] if carrier else None,
                "policy_number": p.get("policy_number"),
                "premium": float(p.get("policy_premium", 0) or 0),
                "effective_date": p.get("policy_effective_date"),
                "expiration_date": p.get("policy_expiration_date"),
            },
            "invoices": invoices,
            "claims": claims,
            "next_action": (
                "Summarize the customer in 2-3 sentences and surface any action "
                "items (overdue invoice, expiring policy, open claim). Offer the "
                "natural next step — usually create_renewal_invoice or create_claim."
            ),
        }

    # ----------------------------------------------------------------------
    # Tool 5 — Create renewal invoice (write + HubSpot sync)
    # ----------------------------------------------------------------------

    @mcp.tool()
    def create_renewal_invoice(
        contact_id: str,
        gross_premium: float | None = None,
    ) -> dict[str, Any]:
        """Create a renewal invoice for the contact's current policy. Pulls
        carrier and policy number from HubSpot. If gross_premium is omitted,
        uses the premium recorded on the HubSpot contact.

        On success: creates the invoice in AgentSnap, creates a deal in
        HubSpot, and logs a timeline note on the contact so the activity
        shows up in the agency's normal HubSpot workflow.

        Triggers the spend cap if gross_premium > $5,000.
        """
        contact = hubspot.get_contact(contact_id)
        if contact is None:
            return {"error": f"Contact {contact_id} not found"}

        p = contact["properties"]
        carrier_name = p.get("carrier")
        policy_number = p.get("policy_number")
        if gross_premium is None:
            try:
                gross_premium = float(p.get("policy_premium", 0) or 0)
            except Exception:
                gross_premium = 0.0

        if not carrier_name or not policy_number:
            return {
                "error": (
                    "Contact is missing carrier or policy_number on their HubSpot "
                    "record. Update the contact in HubSpot before creating an invoice."
                )
            }

        carrier = agentsnap.get_carrier_by_name(carrier_name)
        if carrier is None:
            return {"error": f"Unknown carrier '{carrier_name}' — not in AgentSnap's carrier list"}

        # Spend cap check
        cap_response = safety.check_spend_cap(gross_premium)
        if cap_response is not None and cap_response.get("status") == "blocked":
            return cap_response

        if cap_response is not None and cap_response.get("status") == "awaiting_confirmation":
            # Hold the action and return the confirmation prompt
            def execute_held():
                inv = agentsnap.create_invoice(
                    contact_id=contact_id,
                    carrier_id=carrier["id"],
                    policy_number=policy_number,
                    gross_premium=gross_premium,
                )
                deal = hubspot.create_deal(
                    contact_id=contact_id,
                    dealname=f"Renewal — {p.get('firstname')} {p.get('lastname')} ({carrier_name})",
                    amount=gross_premium,
                )
                hubspot.log_timeline_note(
                    contact_id=contact_id,
                    note=(
                        f"AgentSnap created renewal invoice ${gross_premium:,.2f} "
                        f"with {carrier_name} (policy {policy_number}). "
                        f"HubSpot deal id: {deal['id']}."
                    ),
                )
                safety.audit(
                    "create_invoice",
                    invoice_id=inv["id"],
                    contact_id=contact_id,
                    carrier=carrier_name,
                    amount=gross_premium,
                    confirmed=True,
                )
                return {"invoice": inv, "hubspot_deal": deal}

            safety.hold_for_confirmation(
                confirmation_id=cap_response["confirmation_id"],
                action_callable=execute_held,
                amount=gross_premium,
                description=(
                    f"Renewal invoice ${gross_premium:,.2f} for "
                    f"{p.get('firstname')} {p.get('lastname')} ({carrier_name})"
                ),
            )

            return {
                **cap_response,
                "preview": {
                    "contact": f"{p.get('firstname')} {p.get('lastname')}",
                    "carrier": carrier_name,
                    "policy_number": policy_number,
                    "gross_premium": gross_premium,
                },
                "next_action": (
                    "Tell the user the exact amount, who it's for, and ask for "
                    "explicit yes/no. If yes, call confirm_action with the "
                    "confirmation_id above. If no, the action will simply expire."
                ),
            }

        # Under the cap — execute directly
        invoice = agentsnap.create_invoice(
            contact_id=contact_id,
            carrier_id=carrier["id"],
            policy_number=policy_number,
            gross_premium=gross_premium,
        )
        deal = hubspot.create_deal(
            contact_id=contact_id,
            dealname=f"Renewal — {p.get('firstname')} {p.get('lastname')} ({carrier_name})",
            amount=gross_premium,
        )
        hubspot.log_timeline_note(
            contact_id=contact_id,
            note=(
                f"AgentSnap created renewal invoice ${gross_premium:,.2f} with "
                f"{carrier_name} (policy {policy_number}). HubSpot deal id: {deal['id']}."
            ),
        )
        safety.record_uncapped_spend(gross_premium)
        safety.audit(
            "create_invoice",
            invoice_id=invoice["id"],
            contact_id=contact_id,
            carrier=carrier_name,
            amount=gross_premium,
            confirmed=False,
        )

        return {
            "status": "created",
            "invoice": invoice,
            "hubspot_deal_id": deal["id"],
            "hubspot_timeline_note": "logged",
            "next_action": (
                "Confirm to the user the invoice was created and the deal + "
                "timeline activity were synced to HubSpot. Offer to send the "
                "payment link or look at the next renewal."
            ),
        }

    # ----------------------------------------------------------------------
    # Tool 6 — Confirm a held action
    # ----------------------------------------------------------------------

    @mcp.tool()
    def confirm_action(confirmation_id: str) -> dict[str, Any]:
        """Confirm a previously-held action (one that triggered the spend cap).

        The user must have explicitly said yes to the amount before this is
        called. Returns the executed action's result, or an error if the
        confirmation expired or was already used.
        """
        result = safety.execute_confirmation(confirmation_id)
        if result.get("status") == "confirmed":
            result["next_action"] = (
                "Tell the user the action completed and surface the new invoice id "
                "and HubSpot deal id from result.result. Offer the next step."
            )
        return result

    # ----------------------------------------------------------------------
    # Tool 7 — Create claim
    # ----------------------------------------------------------------------

    @mcp.tool()
    def create_claim(
        contact_id: str,
        claim_type: str,
        description: str,
    ) -> dict[str, Any]:
        """Open a new claim for a contact. claim_type is one of:
        auto, property, liability, other.

        Logs the claim creation as a HubSpot timeline note on the contact.
        """
        valid_types = {"auto", "property", "liability", "other"}
        if claim_type.lower() not in valid_types:
            return {
                "error": (
                    f"claim_type must be one of {sorted(valid_types)} — got '{claim_type}'"
                )
            }

        contact = hubspot.get_contact(contact_id)
        if contact is None:
            return {"error": f"Contact {contact_id} not found"}

        p = contact["properties"]
        carrier_name = p.get("carrier")
        policy_number = p.get("policy_number")
        carrier = agentsnap.get_carrier_by_name(carrier_name) if carrier_name else None
        if carrier is None or not policy_number:
            return {
                "error": (
                    "Contact is missing carrier or policy_number — cannot open a "
                    "claim without those. Update the contact in HubSpot first."
                )
            }

        claim = agentsnap.create_claim(
            contact_id=contact_id,
            carrier_id=carrier["id"],
            policy_number=policy_number,
            claim_type=claim_type.lower(),
            description=description,
        )

        hubspot.log_timeline_note(
            contact_id=contact_id,
            note=(
                f"AgentSnap opened {claim_type.lower()} claim {claim['id']} "
                f"with {carrier_name} (policy {policy_number}). Description: {description}"
            ),
        )

        safety.audit(
            "create_claim",
            claim_id=claim["id"],
            contact_id=contact_id,
            carrier=carrier_name,
            claim_type=claim_type.lower(),
        )

        return {
            "status": "created",
            "claim": claim,
            "hubspot_timeline_note": "logged",
            "next_action": (
                "Tell the user the claim id and that the timeline was updated. "
                "Offer to draft a notification to the insured or to track other claims."
            ),
        }

    # ----------------------------------------------------------------------
    # Tool 8 — List claims
    # ----------------------------------------------------------------------

    @mcp.tool()
    def list_claims(
        contact_id: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """List claims with optional filters by contact_id and status. Status is
        one of: open, under_review, investigating, settled, denied.
        """
        claims = agentsnap.list_claims(contact_id=contact_id, status=status)
        # Decorate with contact names for the LLM
        decorated = []
        for c in claims:
            contact = hubspot.get_contact(c["contact_id"])
            name = ""
            if contact:
                p = contact["properties"]
                name = f"{p.get('firstname', '')} {p.get('lastname', '')}".strip()
            carrier = agentsnap.get_carrier(c["carrier_id"])
            decorated.append({
                **c,
                "contact_name": name,
                "carrier_name": carrier["name"] if carrier else None,
            })

        return {
            "filters": {"contact_id": contact_id, "status": status},
            "count": len(decorated),
            "claims": decorated,
            "next_action": (
                "Summarize the open work, surface the oldest open claim, and "
                "offer to drill into one if the user wants details."
            ),
        }

    # ----------------------------------------------------------------------
    # Tool 9 — Commission status
    # ----------------------------------------------------------------------

    @mcp.tool()
    def get_commission_status() -> dict[str, Any]:
        """Commission earned year-to-date, broken down by carrier and by quarter.

        Derived from paid invoices × carrier commission rate. The real
        SnapRefund API has no /commissions endpoint — this is computed.
        """
        summary = agentsnap.get_commission_summary()
        return {
            **summary,
            "next_action": (
                "Show the user the YTD total first, then break out by carrier. "
                "Quarterly view is available in by_quarter if they want it."
            ),
        }
