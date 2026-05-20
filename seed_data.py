"""Seed data for the AgentSnap HubSpot demo.

Personal-lines focused (auto + home), tuned for a ~20-agent agency.
Dates are calculated relative to "today" so the demo always looks fresh.

The demo references specific named contacts. If you change names here,
update the prompts in README.md too.
"""

from datetime import date, timedelta
from typing import Any

TODAY = date(2026, 5, 20)


def _days_from_today(n: int) -> str:
    """Return an ISO date string for N days from today."""
    return (TODAY + timedelta(days=n)).isoformat()


# ---------------------------------------------------------------------------
# Carriers — match the main AgentSnap mock with the same commission rates
# ---------------------------------------------------------------------------

CARRIERS: list[dict[str, Any]] = [
    {"id": 1, "name": "Hartford", "commission_rate": 0.12},
    {"id": 2, "name": "Progressive", "commission_rate": 0.105},
    {"id": 3, "name": "Nationwide", "commission_rate": 0.11},
    {"id": 4, "name": "Allstate", "commission_rate": 0.13},
]

CARRIER_NAME_TO_ID = {c["name"].lower(): c["id"] for c in CARRIERS}


# ---------------------------------------------------------------------------
# HubSpot contacts — what a personal-lines agency's HubSpot would look like
# ---------------------------------------------------------------------------
# Custom properties used by Hutsenpiller-style agencies on HubSpot:
#   policy_type, carrier, policy_premium, policy_effective_date,
#   policy_expiration_date, policy_number
# These match the property names defined in config.py — change there if your
# HubSpot uses different names.
# ---------------------------------------------------------------------------

HUBSPOT_CONTACTS: list[dict[str, Any]] = [
    {
        "id": "hs_1001",
        "properties": {
            "firstname": "Sarah",
            "lastname": "Johnson",
            "email": "sarah.johnson@example.com",
            "phone": "+1-555-0101",
            "city": "Columbus",
            "state": "OH",
            "policy_type": "Auto",
            "carrier": "Hartford",
            "policy_premium": "1480.00",
            "policy_effective_date": _days_from_today(-352),
            "policy_expiration_date": _days_from_today(13),
            "policy_number": "HF-AUTO-23491",
        },
    },
    {
        "id": "hs_1002",
        "properties": {
            "firstname": "Mike",
            "lastname": "Chen",
            "email": "mike.chen@example.com",
            "phone": "+1-555-0102",
            "city": "Cleveland",
            "state": "OH",
            "policy_type": "Bundle",
            "carrier": "Progressive",
            "policy_premium": "2210.00",
            "policy_effective_date": _days_from_today(-365),
            "policy_expiration_date": _days_from_today(0),  # expires today — overdue territory
            "policy_number": "PG-BUND-88123",
        },
    },
    {
        "id": "hs_1003",
        "properties": {
            "firstname": "Lisa",
            "lastname": "Patel",
            "email": "lisa.patel@example.com",
            "phone": "+1-555-0103",
            "city": "Cincinnati",
            "state": "OH",
            "policy_type": "Home",
            "carrier": "Allstate",
            "policy_premium": "1920.00",
            "policy_effective_date": _days_from_today(-330),
            "policy_expiration_date": _days_from_today(35),
            "policy_number": "AS-HOME-44021",
        },
    },
    {
        "id": "hs_1004",
        "properties": {
            "firstname": "Tom",
            "lastname": "Wright",
            "email": "tom.wright@example.com",
            "phone": "+1-555-0104",
            "city": "Dayton",
            "state": "OH",
            "policy_type": "Auto",
            "carrier": "Hartford",
            "policy_premium": "1140.00",
            "policy_effective_date": _days_from_today(-344),
            "policy_expiration_date": _days_from_today(21),
            "policy_number": "HF-AUTO-23492",
        },
    },
    {
        "id": "hs_1005",
        "properties": {
            "firstname": "Amy",
            "lastname": "Davis",
            "email": "amy.davis@example.com",
            "phone": "+1-555-0105",
            "city": "Akron",
            "state": "OH",
            "policy_type": "Home",
            "carrier": "Nationwide",
            "policy_premium": "1675.00",
            "policy_effective_date": _days_from_today(-310),
            "policy_expiration_date": _days_from_today(55),
            "policy_number": "NW-HOME-77104",
        },
    },
    {
        "id": "hs_1006",
        "properties": {
            "firstname": "Robert",
            "lastname": "Martinez",
            "email": "robert.martinez@example.com",
            "phone": "+1-555-0106",
            "city": "Toledo",
            "state": "OH",
            "policy_type": "Bundle",
            "carrier": "Hartford",
            "policy_premium": "7820.00",  # high premium — trips spend cap
            "policy_effective_date": _days_from_today(-360),
            "policy_expiration_date": _days_from_today(5),
            "policy_number": "HF-BUND-99001",
        },
    },
    {
        "id": "hs_1007",
        "properties": {
            "firstname": "Jennifer",
            "lastname": "Lee",
            "email": "jennifer.lee@example.com",
            "phone": "+1-555-0107",
            "city": "Columbus",
            "state": "OH",
            "policy_type": "Auto",
            "carrier": "Progressive",
            "policy_premium": "980.00",
            "policy_effective_date": _days_from_today(-300),
            "policy_expiration_date": _days_from_today(65),
            "policy_number": "PG-AUTO-13345",
        },
    },
    {
        "id": "hs_1008",
        "properties": {
            "firstname": "David",
            "lastname": "Thompson",
            "email": "david.thompson@example.com",
            "phone": "+1-555-0108",
            "city": "Cleveland",
            "state": "OH",
            "policy_type": "Auto",
            "carrier": "Allstate",
            "policy_premium": "1340.00",
            "policy_effective_date": _days_from_today(-290),
            "policy_expiration_date": _days_from_today(75),
            "policy_number": "AS-AUTO-66201",
        },
    },
    {
        "id": "hs_1009",
        "properties": {
            "firstname": "Karen",
            "lastname": "Walker",
            "email": "karen.walker@example.com",
            "phone": "+1-555-0109",
            "city": "Cincinnati",
            "state": "OH",
            "policy_type": "Home",
            "carrier": "Progressive",
            "policy_premium": "2050.00",
            "policy_effective_date": _days_from_today(-280),
            "policy_expiration_date": _days_from_today(85),
            "policy_number": "PG-HOME-50012",
        },
    },
    {
        "id": "hs_1010",
        "properties": {
            "firstname": "James",
            "lastname": "Anderson",
            "email": "james.anderson@example.com",
            "phone": "+1-555-0110",
            "city": "Columbus",
            "state": "OH",
            "policy_type": "Bundle",
            "carrier": "Nationwide",
            "policy_premium": "3210.00",
            "policy_effective_date": _days_from_today(-360),
            "policy_expiration_date": _days_from_today(2),
            "policy_number": "NW-BUND-31221",
        },
    },
    {
        "id": "hs_1011",
        "properties": {
            "firstname": "Patricia",
            "lastname": "Garcia",
            "email": "patricia.garcia@example.com",
            "phone": "+1-555-0111",
            "city": "Akron",
            "state": "OH",
            "policy_type": "Auto",
            "carrier": "Hartford",
            "policy_premium": "1180.00",
            "policy_effective_date": _days_from_today(-200),
            "policy_expiration_date": _days_from_today(165),
            "policy_number": "HF-AUTO-23493",
        },
    },
    {
        "id": "hs_1012",
        "properties": {
            "firstname": "Mark",
            "lastname": "Stevens",
            "email": "mark.stevens@example.com",
            "phone": "+1-555-0112",
            "city": "Toledo",
            "state": "OH",
            "policy_type": "Home",
            "carrier": "Allstate",
            "policy_premium": "1850.00",
            "policy_effective_date": _days_from_today(-180),
            "policy_expiration_date": _days_from_today(185),
            "policy_number": "AS-HOME-44022",
        },
    },
]


# ---------------------------------------------------------------------------
# AgentSnap state — what the operations layer would store
# ---------------------------------------------------------------------------

# Invoices reference HubSpot contact_id. Invoices created by the demo are
# appended to this list at runtime, mirrored to HubSpot as deals.

INVOICES: list[dict[str, Any]] = [
    # An older paid renewal — for commission history
    {
        "id": 5001,
        "contact_id": "hs_1011",
        "carrier_id": CARRIER_NAME_TO_ID["hartford"],
        "policy_number": "HF-AUTO-23493",
        "gross_premium": 1180.00,
        "status": "paid",
        "effective_date": _days_from_today(-185),
        "paid_date": _days_from_today(-180),
    },
    {
        "id": 5002,
        "contact_id": "hs_1012",
        "carrier_id": CARRIER_NAME_TO_ID["allstate"],
        "policy_number": "AS-HOME-44022",
        "gross_premium": 1850.00,
        "status": "paid",
        "effective_date": _days_from_today(-170),
        "paid_date": _days_from_today(-165),
    },
    # Overdue invoice — for daily briefing
    {
        "id": 5003,
        "contact_id": "hs_1002",
        "carrier_id": CARRIER_NAME_TO_ID["progressive"],
        "policy_number": "PG-BUND-88123",
        "gross_premium": 2210.00,
        "status": "overdue",
        "effective_date": _days_from_today(-25),
        "paid_date": None,
    },
    # Payment link sent, not yet paid
    {
        "id": 5004,
        "contact_id": "hs_1004",
        "carrier_id": CARRIER_NAME_TO_ID["hartford"],
        "policy_number": "HF-AUTO-23492",
        "gross_premium": 1140.00,
        "status": "payment_link_pending",
        "effective_date": _days_from_today(-3),
        "paid_date": None,
    },
    # More paid — for commission quarterly breakdown
    {
        "id": 5005,
        "contact_id": "hs_1003",
        "carrier_id": CARRIER_NAME_TO_ID["allstate"],
        "policy_number": "AS-HOME-44021",
        "gross_premium": 1920.00,
        "status": "paid",
        "effective_date": _days_from_today(-95),
        "paid_date": _days_from_today(-90),
    },
    {
        "id": 5006,
        "contact_id": "hs_1005",
        "carrier_id": CARRIER_NAME_TO_ID["nationwide"],
        "policy_number": "NW-HOME-77104",
        "gross_premium": 1675.00,
        "status": "paid",
        "effective_date": _days_from_today(-60),
        "paid_date": _days_from_today(-55),
    },
    {
        "id": 5007,
        "contact_id": "hs_1007",
        "carrier_id": CARRIER_NAME_TO_ID["progressive"],
        "policy_number": "PG-AUTO-13345",
        "gross_premium": 980.00,
        "status": "paid",
        "effective_date": _days_from_today(-40),
        "paid_date": _days_from_today(-38),
    },
    # -----------------------------------------------------------------------
    # Earlier-in-2026 renewals — prior policy terms now historical.
    # These make YTD commission look realistic for a single producer at a
    # ~20-agent personal-lines shop (~$6-8K by mid-May).
    # -----------------------------------------------------------------------
    {
        "id": 5008,
        "contact_id": "hs_1001",
        "carrier_id": CARRIER_NAME_TO_ID["hartford"],
        "policy_number": "HF-AUTO-23491-PR",
        "gross_premium": 1440.00,
        "status": "paid",
        "effective_date": _days_from_today(-130),
        "paid_date": _days_from_today(-128),
    },
    {
        "id": 5009,
        "contact_id": "hs_1004",
        "carrier_id": CARRIER_NAME_TO_ID["hartford"],
        "policy_number": "HF-AUTO-23492-PR",
        "gross_premium": 1140.00,
        "status": "paid",
        "effective_date": _days_from_today(-125),
        "paid_date": _days_from_today(-122),
    },
    {
        "id": 5010,
        "contact_id": "hs_1006",
        "carrier_id": CARRIER_NAME_TO_ID["hartford"],
        "policy_number": "HF-BUND-99001-PR",
        "gross_premium": 6800.00,
        "status": "paid",
        "effective_date": _days_from_today(-120),
        "paid_date": _days_from_today(-117),
    },
    {
        "id": 5011,
        "contact_id": "hs_1010",
        "carrier_id": CARRIER_NAME_TO_ID["nationwide"],
        "policy_number": "NW-BUND-31221-PR",
        "gross_premium": 3150.00,
        "status": "paid",
        "effective_date": _days_from_today(-110),
        "paid_date": _days_from_today(-108),
    },
    {
        "id": 5012,
        "contact_id": "hs_1008",
        "carrier_id": CARRIER_NAME_TO_ID["allstate"],
        "policy_number": "AS-AUTO-66201-PR",
        "gross_premium": 1340.00,
        "status": "paid",
        "effective_date": _days_from_today(-100),
        "paid_date": _days_from_today(-97),
    },
    {
        "id": 5013,
        "contact_id": "hs_1009",
        "carrier_id": CARRIER_NAME_TO_ID["progressive"],
        "policy_number": "PG-BUND-50012-PR",
        "gross_premium": 4250.00,
        "status": "paid",
        "effective_date": _days_from_today(-90),
        "paid_date": _days_from_today(-87),
    },
    {
        "id": 5014,
        "contact_id": "hs_1002",
        "carrier_id": CARRIER_NAME_TO_ID["progressive"],
        "policy_number": "PG-BUND-88123-PR",
        "gross_premium": 2150.00,
        "status": "paid",
        "effective_date": _days_from_today(-75),
        "paid_date": _days_from_today(-72),
    },
    {
        "id": 5015,
        "contact_id": "hs_1011",
        "carrier_id": CARRIER_NAME_TO_ID["hartford"],
        "policy_number": "HF-AUTO-23493-PR2",
        "gross_premium": 1180.00,
        "status": "paid",
        "effective_date": _days_from_today(-55),
        "paid_date": _days_from_today(-52),
    },
    # ---- Q2 2026 paid invoices (Apr - mid-May) ----
    {
        "id": 5016,
        "contact_id": "hs_1012",
        "carrier_id": CARRIER_NAME_TO_ID["allstate"],
        "policy_number": "AS-HOME-44022-PR2",
        "gross_premium": 1850.00,
        "status": "paid",
        "effective_date": _days_from_today(-40),
        "paid_date": _days_from_today(-38),
    },
    {
        "id": 5017,
        "contact_id": "hs_1006",
        "carrier_id": CARRIER_NAME_TO_ID["hartford"],
        "policy_number": "HF-UMB-99001-EN",  # umbrella endorsement
        "gross_premium": 2400.00,
        "status": "paid",
        "effective_date": _days_from_today(-28),
        "paid_date": _days_from_today(-25),
    },
    {
        "id": 5018,
        "contact_id": "hs_1010",
        "carrier_id": CARRIER_NAME_TO_ID["nationwide"],
        "policy_number": "NW-AUTO-31221-AD",  # auto add-on
        "gross_premium": 1450.00,
        "status": "paid",
        "effective_date": _days_from_today(-22),
        "paid_date": _days_from_today(-19),
    },
    {
        "id": 5019,
        "contact_id": "hs_1005",
        "carrier_id": CARRIER_NAME_TO_ID["nationwide"],
        "policy_number": "NW-BUND-77104-CS",  # cross-sell bundle
        "gross_premium": 2300.00,
        "status": "paid",
        "effective_date": _days_from_today(-18),
        "paid_date": _days_from_today(-15),
    },
    {
        "id": 5020,
        "contact_id": "hs_1008",
        "carrier_id": CARRIER_NAME_TO_ID["allstate"],
        "policy_number": "AS-HOME-66201-CS",  # cross-sell home
        "gross_premium": 1650.00,
        "status": "paid",
        "effective_date": _days_from_today(-8),
        "paid_date": _days_from_today(-5),
    },
    {
        "id": 5021,
        "contact_id": "hs_1003",
        "carrier_id": CARRIER_NAME_TO_ID["allstate"],
        "policy_number": "AS-BUND-44021-CS",  # cross-sell bundle
        "gross_premium": 4200.00,
        "status": "paid",
        "effective_date": _days_from_today(-12),
        "paid_date": _days_from_today(-9),
    },
]


CLAIMS: list[dict[str, Any]] = [
    {
        "id": "CL-2026-0142",
        "contact_id": "hs_1001",
        "carrier_id": CARRIER_NAME_TO_ID["hartford"],
        "policy_number": "HF-AUTO-23491",
        "claim_type": "auto",
        "status": "under_review",
        "description": "Rear-end collision, no injuries reported",
        "opened_date": _days_from_today(-12),
        "amount": None,
    },
    {
        "id": "CL-2026-0138",
        "contact_id": "hs_1002",
        "carrier_id": CARRIER_NAME_TO_ID["progressive"],
        "policy_number": "PG-BUND-88123",
        "claim_type": "property",
        "status": "settled",
        "description": "Hail damage to roof",
        "opened_date": _days_from_today(-45),
        "amount": 12400.00,
    },
    {
        "id": "CL-2026-0151",
        "contact_id": "hs_1004",
        "carrier_id": CARRIER_NAME_TO_ID["hartford"],
        "policy_number": "HF-AUTO-23492",
        "claim_type": "auto",
        "status": "open",
        "description": "Windshield damage from road debris",
        "opened_date": _days_from_today(-5),
        "amount": None,
    },
    {
        "id": "CL-2026-0145",
        "contact_id": "hs_1003",
        "carrier_id": CARRIER_NAME_TO_ID["allstate"],
        "policy_number": "AS-HOME-44021",
        "claim_type": "liability",
        "status": "investigating",
        "description": "Slip and fall on premises",
        "opened_date": _days_from_today(-20),
        "amount": None,
    },
]


# ---------------------------------------------------------------------------
# Mutable runtime state — invoices and claims created during the demo
# ---------------------------------------------------------------------------

RUNTIME_INVOICES: list[dict[str, Any]] = []
RUNTIME_CLAIMS: list[dict[str, Any]] = []
RUNTIME_HUBSPOT_TIMELINE: list[dict[str, Any]] = []  # mirrors timeline events written back
RUNTIME_HUBSPOT_DEALS: list[dict[str, Any]] = []
