"""Backend clients for the AgentSnap HubSpot demo.

Two clients:
  - HubSpotClient: dual-mode (mock or live). Live mode hits the real HubSpot
    CRM v3 API using a private app token.
  - AgentSnapClient: mock only. Wraps the seed data and mutable runtime state.

The clients expose the operations the MCP tools need. Tools never reach into
seed_data directly — they go through these clients, so swapping mock for live
is a single-line change in MCP server setup.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

import httpx

import config
import seed_data


# ===========================================================================
# HubSpot client
# ===========================================================================


class HubSpotClient:
    """HubSpot CRM v3 client. Mock by default, live if HUBSPOT_PRIVATE_APP_TOKEN is set."""

    def __init__(self) -> None:
        self.mode = config.HUBSPOT_MODE
        self.token = config.HUBSPOT_PRIVATE_APP_TOKEN
        self._http: httpx.Client | None = None

    # -----------------------------------------------------------------------
    # Internal HTTP helper for live mode
    # -----------------------------------------------------------------------

    def _client(self) -> httpx.Client:
        if self._http is None:
            self._http = httpx.Client(
                base_url=config.HUBSPOT_API_BASE,
                timeout=config.HUBSPOT_TIMEOUT_SECONDS,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                },
            )
        return self._http

    # -----------------------------------------------------------------------
    # Read operations
    # -----------------------------------------------------------------------

    def search_contacts(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search contacts by name/email/phone. Returns a list of contact dicts."""
        if self.mode == "mock":
            q = query.lower().strip()
            results = []
            for c in seed_data.HUBSPOT_CONTACTS:
                props = c["properties"]
                blob = " ".join(
                    str(v) for v in (props.get("firstname"), props.get("lastname"),
                                     props.get("email"), props.get("phone"))
                ).lower()
                if q in blob:
                    results.append(c)
                    if len(results) >= limit:
                        break
            return results

        # Live mode — HubSpot Search API
        payload = {
            "filterGroups": [
                {
                    "filters": [
                        {"propertyName": "email", "operator": "CONTAINS_TOKEN", "value": query}
                    ]
                },
                {
                    "filters": [
                        {"propertyName": "firstname", "operator": "CONTAINS_TOKEN", "value": query}
                    ]
                },
                {
                    "filters": [
                        {"propertyName": "lastname", "operator": "CONTAINS_TOKEN", "value": query}
                    ]
                },
                {
                    "filters": [
                        {"propertyName": "phone", "operator": "CONTAINS_TOKEN", "value": query}
                    ]
                },
            ],
            "properties": config.HUBSPOT_ALL_CONTACT_PROPERTIES,
            "limit": limit,
        }
        resp = self._client().post("/crm/v3/objects/contacts/search", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return [{"id": r["id"], "properties": r.get("properties", {})} for r in data.get("results", [])]

    def get_contact(self, contact_id: str) -> dict[str, Any] | None:
        """Get a single contact by HubSpot ID."""
        if self.mode == "mock":
            for c in seed_data.HUBSPOT_CONTACTS:
                if c["id"] == contact_id:
                    return c
            return None

        params = {"properties": ",".join(config.HUBSPOT_ALL_CONTACT_PROPERTIES)}
        resp = self._client().get(f"/crm/v3/objects/contacts/{contact_id}", params=params)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
        return {"id": data["id"], "properties": data.get("properties", {})}

    def list_contacts_with_expiring_policies(self, days_ahead: int) -> list[dict[str, Any]]:
        """Return contacts whose policy expires within `days_ahead` days from today.

        Live mode is implemented as a Search API call filtering by the
        policy_expiration_date property. Mock mode reads seed data.
        """
        today_iso = seed_data.TODAY.isoformat()
        cutoff_iso = seed_data._days_from_today(days_ahead)

        if self.mode == "mock":
            results = []
            for c in seed_data.HUBSPOT_CONTACTS:
                exp = c["properties"].get("policy_expiration_date")
                if exp and today_iso <= exp <= cutoff_iso:
                    results.append(c)
            return results

        exp_prop = config.HUBSPOT_PROPERTIES["policy_expiration_date"]
        payload = {
            "filterGroups": [
                {
                    "filters": [
                        {"propertyName": exp_prop, "operator": "GTE", "value": today_iso},
                        {"propertyName": exp_prop, "operator": "LTE", "value": cutoff_iso},
                    ]
                }
            ],
            "properties": config.HUBSPOT_ALL_CONTACT_PROPERTIES,
            "sorts": [{"propertyName": exp_prop, "direction": "ASCENDING"}],
            "limit": 100,
        }
        resp = self._client().post("/crm/v3/objects/contacts/search", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return [{"id": r["id"], "properties": r.get("properties", {})} for r in data.get("results", [])]

    # -----------------------------------------------------------------------
    # Write operations — these are what makes the demo feel real
    # -----------------------------------------------------------------------

    def create_deal(
        self,
        contact_id: str,
        dealname: str,
        amount: float,
        pipeline_stage: str = "appointmentscheduled",
    ) -> dict[str, Any]:
        """Create a HubSpot deal and associate it with the contact.

        The deal represents the renewal/invoice in HubSpot's CRM, so CJ can see
        it in his normal HubSpot workflow alongside his other deals.
        """
        if self.mode == "mock":
            deal_id = f"deal_{int(time.time() * 1000)}"
            deal = {
                "id": deal_id,
                "properties": {
                    "dealname": dealname,
                    "amount": f"{amount:.2f}",
                    "dealstage": pipeline_stage,
                    "createdate": datetime.now(timezone.utc).isoformat(),
                },
                "associated_contact_id": contact_id,
            }
            seed_data.RUNTIME_HUBSPOT_DEALS.append(deal)
            return deal

        # Live mode
        payload = {
            "properties": {
                "dealname": dealname,
                "amount": f"{amount:.2f}",
                "dealstage": pipeline_stage,
            },
            "associations": [
                {
                    "to": {"id": contact_id},
                    "types": [
                        {
                            "associationCategory": "HUBSPOT_DEFINED",
                            "associationTypeId": 3,  # contact-to-deal
                        }
                    ],
                }
            ],
        }
        resp = self._client().post("/crm/v3/objects/deals", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return {"id": data["id"], "properties": data.get("properties", {}), "associated_contact_id": contact_id}

    def log_timeline_note(self, contact_id: str, note: str) -> dict[str, Any]:
        """Log a timeline note on a contact. This is how AgentSnap actions show
        up in HubSpot's contact timeline — the same place CJ already looks for
        contact history.
        """
        if self.mode == "mock":
            event = {
                "id": f"note_{int(time.time() * 1000)}",
                "contact_id": contact_id,
                "body": note,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            seed_data.RUNTIME_HUBSPOT_TIMELINE.append(event)
            return event

        # Live mode — use the Notes engagement (timeline event)
        payload = {
            "properties": {
                "hs_note_body": note,
                "hs_timestamp": datetime.now(timezone.utc).isoformat(),
            },
            "associations": [
                {
                    "to": {"id": contact_id},
                    "types": [
                        {
                            "associationCategory": "HUBSPOT_DEFINED",
                            "associationTypeId": 202,  # note-to-contact
                        }
                    ],
                }
            ],
        }
        resp = self._client().post("/crm/v3/objects/notes", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return {"id": data["id"], "contact_id": contact_id, "body": note}


# ===========================================================================
# AgentSnap mock client
# ===========================================================================


class AgentSnapClient:
    """Mock AgentSnap backend. Wraps the seed invoices/claims/carriers and
    appends runtime state for actions taken during the demo.
    """

    # ---- Carriers -----

    def list_carriers(self) -> list[dict[str, Any]]:
        return list(seed_data.CARRIERS)

    def get_carrier_by_name(self, name: str) -> dict[str, Any] | None:
        for c in seed_data.CARRIERS:
            if c["name"].lower() == name.lower():
                return c
        return None

    def get_carrier(self, carrier_id: int) -> dict[str, Any] | None:
        for c in seed_data.CARRIERS:
            if c["id"] == carrier_id:
                return c
        return None

    # ---- Invoices -----

    def list_invoices(
        self,
        contact_id: str | None = None,
        carrier_id: int | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        all_invoices = seed_data.INVOICES + seed_data.RUNTIME_INVOICES
        result = []
        for inv in all_invoices:
            if contact_id and inv["contact_id"] != contact_id:
                continue
            if carrier_id and inv["carrier_id"] != carrier_id:
                continue
            if status and inv["status"] != status:
                continue
            result.append(inv)
        return result

    def create_invoice(
        self,
        contact_id: str,
        carrier_id: int,
        policy_number: str,
        gross_premium: float,
    ) -> dict[str, Any]:
        new_id = 5000 + len(seed_data.INVOICES) + len(seed_data.RUNTIME_INVOICES) + 1
        invoice = {
            "id": new_id,
            "contact_id": contact_id,
            "carrier_id": carrier_id,
            "policy_number": policy_number,
            "gross_premium": float(gross_premium),
            "status": "payment_link_pending",
            "effective_date": seed_data.TODAY.isoformat(),
            "paid_date": None,
        }
        seed_data.RUNTIME_INVOICES.append(invoice)
        return invoice

    # ---- Claims -----

    def list_claims(
        self,
        contact_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        all_claims = seed_data.CLAIMS + seed_data.RUNTIME_CLAIMS
        result = []
        for claim in all_claims:
            if contact_id and claim["contact_id"] != contact_id:
                continue
            if status and claim["status"] != status:
                continue
            result.append(claim)
        return result

    def create_claim(
        self,
        contact_id: str,
        carrier_id: int,
        policy_number: str,
        claim_type: str,
        description: str,
    ) -> dict[str, Any]:
        next_seq = len(seed_data.CLAIMS) + len(seed_data.RUNTIME_CLAIMS) + 1
        claim_id = f"CL-2026-{next_seq:04d}"
        claim = {
            "id": claim_id,
            "contact_id": contact_id,
            "carrier_id": carrier_id,
            "policy_number": policy_number,
            "claim_type": claim_type,
            "status": "open",
            "description": description,
            "opened_date": seed_data.TODAY.isoformat(),
            "amount": None,
        }
        seed_data.RUNTIME_CLAIMS.append(claim)
        return claim

    # ---- Commissions (derived from invoices) -----

    def get_commission_summary(self) -> dict[str, Any]:
        """Commission earned this quarter, broken down by carrier."""
        from collections import defaultdict
        from datetime import date

        all_invoices = seed_data.INVOICES + seed_data.RUNTIME_INVOICES
        paid = [inv for inv in all_invoices if inv["status"] == "paid"]

        # Group by quarter
        by_quarter: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        total_by_carrier: dict[str, float] = defaultdict(float)
        ytd_total = 0.0

        for inv in paid:
            eff = date.fromisoformat(inv["effective_date"])
            if eff.year != seed_data.TODAY.year:
                continue
            quarter = f"Q{((eff.month - 1) // 3) + 1}"
            carrier = self.get_carrier(inv["carrier_id"])
            if carrier is None:
                continue
            commission = inv["gross_premium"] * carrier["commission_rate"]
            by_quarter[quarter][carrier["name"]] += commission
            total_by_carrier[carrier["name"]] += commission
            ytd_total += commission

        return {
            "year": seed_data.TODAY.year,
            "ytd_total": round(ytd_total, 2),
            "by_carrier": {k: round(v, 2) for k, v in total_by_carrier.items()},
            "by_quarter": {
                q: {k: round(v, 2) for k, v in carriers.items()}
                for q, carriers in by_quarter.items()
            },
        }
