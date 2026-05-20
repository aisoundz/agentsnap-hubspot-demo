# AgentSnap MCP — HubSpot Edition (Demo)

A working demo of AgentSnap MCP using **HubSpot as the system of record** instead of a traditional AMS. Built for independent agencies on HubSpot, Salesforce, or custom CRM stacks.

## What this is

A Claude Desktop MCP server you can install in 5 minutes. Once installed, Claude can do real operations work — pull up customer profiles, advance renewals, open claims, reconcile commissions — and **everything syncs back to HubSpot** as deals and timeline activities.

Two modes, your choice:

- **Mock mode (zero setup).** Rich seed data baked in. Install, restart Claude, try it.
- **Live HubSpot mode.** Generate a HubSpot private app token, drop it in, and Claude reads and writes against your real contacts.

## What it can do

9 tools, wired into a complete demo flow:

| Tool | What it does |
|---|---|
| `get_daily_briefing` | Snapshot: urgent renewals, overdue invoices, open claims, commission YTD |
| `get_renewal_pipeline` | Policies expiring in the next N days, sorted urgent first |
| `search_contact` | Find a HubSpot contact by name, email, or phone |
| `get_contact_full` | Full profile: HubSpot data + policies + invoices + claims |
| `create_renewal_invoice` | Generate a renewal invoice → syncs as a HubSpot deal + timeline note |
| `confirm_action` | Confirm a held action (triggers when premium > $5,000 spend cap) |
| `create_claim` | Open a claim → logs to HubSpot timeline |
| `list_claims` | View claims with optional filters |
| `get_commission_status` | Earnings YTD by carrier + quarterly breakdown |

## Install in 5 minutes

```bash
# 1. Clone or unzip somewhere
cd ~/Documents/agentsnap-hubspot-demo

# 2. Set up Python (3.10+)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Verify it imports
python -c "import server; print('OK')"

# 4. Wire it into Claude Desktop — see INSTALL.md for details
```

Open Claude Desktop, restart, and ask: **"What's on my plate today?"**

## Want to point it at your real HubSpot?

See [INSTALL.md](./INSTALL.md) for the private app token walkthrough. Two minutes of setup, then every demo prompt runs against your live data.

## Try these 8 prompts

Once installed, ask Claude in order:

1. **"What's on my plate today?"**
2. **"Show me everyone whose policy expires in the next 30 days."**
3. **"Look up Robert Martinez."**
4. **"Renew Sarah Johnson's policy."**
5. **"Renew Robert Martinez's Hartford policy."** *(triggers the $5K spend cap — Claude will ask you to confirm)*
6. **"Yes, confirm."**
7. **"Open a property claim for Mike Chen — water damage to the basement."**
8. **"How much commission did I earn this quarter?"**

Each one demonstrates a different piece of the operations layer.

## What's actually happening under the hood

In **mock mode**, contacts and policies come from `seed_data.py` and writes are appended to in-memory runtime state. No network calls.

In **live mode**, the HubSpot client (`backends.py`) hits the HubSpot CRM v3 API:
- `POST /crm/v3/objects/contacts/search` for searches
- `GET /crm/v3/objects/contacts/{id}` for profile pulls
- `POST /crm/v3/objects/deals` (with contact association) for invoice sync
- `POST /crm/v3/objects/notes` (with contact association) for timeline notes

AgentSnap-side state (invoices, claims, commissions) is still mock — that's the SnapRefund/AgentSnap backend, which is a separate service in production.

## Safety

Every write action is gated:

- **Per-transaction limit:** $5,000. Anything larger returns a held action with a `confirmation_id`. Claude must ask the user for explicit yes/no before calling `confirm_action`.
- **Daily limit:** $20,000 in confirmed writes per agency per day.
- **Audit log:** every state-changing action appends to `audit_log.jsonl` in the demo directory. Open it after the demo to see exactly what was logged.

## File map

```
agentsnap-hubspot-demo/
├── README.md                       # This file
├── INSTALL.md                      # Detailed install + HubSpot token walkthrough
├── server.py                       # FastMCP entry point
├── tools.py                        # 9 MCP tools
├── backends.py                     # HubSpot client (mock + live) + AgentSnap client
├── seed_data.py                    # Mock HubSpot contacts, policies, claims
├── safety.py                       # Spend caps + audit log
├── config.py                       # Mode switch + HubSpot property name mapping
├── claude_desktop_config.example.json
├── requirements.txt
├── demo_landing.html               # Standalone landing page for sharing
└── audit_log.jsonl                 # Created at runtime — every action logged here
```

## Questions, feedback, problems

Reply to the email Anis sent. The demo is designed for fast iteration — if something feels off, the patch usually ships the same week.
