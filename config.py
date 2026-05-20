"""Configuration for the AgentSnap HubSpot demo.

Two modes are supported:

1. **Mock mode** (default): no setup. Demo runs against the seed data in
   seed_data.py. Good for first-look or sharing with someone without giving
   them HubSpot credentials.

2. **Live HubSpot mode**: set HUBSPOT_PRIVATE_APP_TOKEN in your environment
   (or in claude_desktop_config.json) and the demo will read/write against
   your real HubSpot account.

To create a HubSpot private app token:
  HubSpot → Settings → Integrations → Private Apps → Create private app
  Required scopes:
    - crm.objects.contacts.read
    - crm.objects.contacts.write
    - crm.objects.deals.read
    - crm.objects.deals.write
    - crm.objects.notes.write   (or use Engagements API for timeline events)
"""

import os

# ---------------------------------------------------------------------------
# Mode
# ---------------------------------------------------------------------------

HUBSPOT_PRIVATE_APP_TOKEN = os.environ.get("HUBSPOT_PRIVATE_APP_TOKEN", "").strip()
HUBSPOT_MODE = "live" if HUBSPOT_PRIVATE_APP_TOKEN else "mock"


# ---------------------------------------------------------------------------
# HubSpot custom property names
# ---------------------------------------------------------------------------
# Hutsenpiller-style agencies on HubSpot typically have custom contact
# properties for policy data. If your HubSpot uses different property names,
# override them here.
# ---------------------------------------------------------------------------

HUBSPOT_PROPERTIES = {
    "policy_type": os.environ.get("HS_PROP_POLICY_TYPE", "policy_type"),
    "carrier": os.environ.get("HS_PROP_CARRIER", "carrier"),
    "policy_premium": os.environ.get("HS_PROP_POLICY_PREMIUM", "policy_premium"),
    "policy_effective_date": os.environ.get("HS_PROP_POLICY_EFFECTIVE", "policy_effective_date"),
    "policy_expiration_date": os.environ.get("HS_PROP_POLICY_EXPIRATION", "policy_expiration_date"),
    "policy_number": os.environ.get("HS_PROP_POLICY_NUMBER", "policy_number"),
}

# Standard HubSpot contact properties we always want
HUBSPOT_STANDARD_PROPERTIES = [
    "firstname",
    "lastname",
    "email",
    "phone",
    "city",
    "state",
]

HUBSPOT_ALL_CONTACT_PROPERTIES = HUBSPOT_STANDARD_PROPERTIES + list(HUBSPOT_PROPERTIES.values())


# ---------------------------------------------------------------------------
# Spend cap configuration
# ---------------------------------------------------------------------------

PER_TRANSACTION_LIMIT = 5000.00  # dollars — above this requires confirmation
DAILY_LIMIT = 20000.00  # dollars — running total of confirmed writes per day


# ---------------------------------------------------------------------------
# HubSpot API
# ---------------------------------------------------------------------------

HUBSPOT_API_BASE = "https://api.hubapi.com"
HUBSPOT_TIMEOUT_SECONDS = 15


# ---------------------------------------------------------------------------
# Demo agency identity (for audit logs and HubSpot timeline activities)
# ---------------------------------------------------------------------------

AGENCY_ID = os.environ.get("AGENCY_ID", "agency_demo_001")
AGENT_NAME = os.environ.get("AGENT_NAME", "AgentSnap (demo)")
