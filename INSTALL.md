# Install Guide — AgentSnap HubSpot Demo

Two paths. Mock takes 5 minutes; live HubSpot takes about 10 with the token setup.

---

## Path 1 — Mock mode (try without HubSpot creds)

### 1. Python environment

You need Python 3.10 or newer.

```bash
cd ~/Documents/agentsnap-hubspot-demo
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Quick sanity check that everything imports:

```bash
python -c "import server; print('OK')"
```

You should see `OK`. If you see an `ImportError`, the most common cause is that the `mcp` package isn't installed — re-run `pip install -r requirements.txt`.

### 2. Claude Desktop config

Open Claude Desktop's config file. On macOS:

```bash
open -e ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

On Windows:

```
%APPDATA%\Claude\claude_desktop_config.json
```

Add (or merge) the following block. Use the absolute path to your `.venv/bin/python` and `server.py`.

```json
{
  "mcpServers": {
    "agentsnap-hubspot-demo": {
      "command": "/Users/YOU/Documents/agentsnap-hubspot-demo/.venv/bin/python",
      "args": ["/Users/YOU/Documents/agentsnap-hubspot-demo/server.py"]
    }
  }
}
```

### 3. Restart Claude Desktop

Quit completely and reopen. The new MCP server will appear in the connector list as **AgentSnap HubSpot Demo (mock)**.

### 4. Try it

Ask Claude:

> What's on my plate today?

If everything is wired correctly, Claude calls `get_daily_briefing` and walks you through the agency's open work. Continue with the prompts in the README.

---

## Path 2 — Live HubSpot mode (point at your real account)

Everything above, plus a token.

### Generate a HubSpot private app token

1. In HubSpot, click the settings gear (top right).
2. Left sidebar: **Integrations → Private Apps**.
3. **Create a private app**.
4. Name it something like `AgentSnap Demo`.
5. On the **Scopes** tab, enable:

| Scope | Why |
|---|---|
| `crm.objects.contacts.read` | Pull contacts (and the policy custom properties) |
| `crm.objects.contacts.write` | (Optional — only needed if AgentSnap should ever update a contact) |
| `crm.objects.deals.read` | Look up existing deals |
| `crm.objects.deals.write` | Create renewal deals |
| `crm.objects.notes.write` | Log timeline activities |

6. Click **Create app** → copy the **access token**.

### Wire the token into Claude Desktop

Update the same `claude_desktop_config.json` entry to include an `env` block:

```json
{
  "mcpServers": {
    "agentsnap-hubspot-demo": {
      "command": "/Users/YOU/Documents/agentsnap-hubspot-demo/.venv/bin/python",
      "args": ["/Users/YOU/Documents/agentsnap-hubspot-demo/server.py"],
      "env": {
        "HUBSPOT_PRIVATE_APP_TOKEN": "pat-na1-XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
      }
    }
  }
}
```

### Restart Claude Desktop

The server now starts in live mode. The MCP connector name flips to **AgentSnap HubSpot Demo (live)**, and every search/read/write goes against your real HubSpot account.

### Heads-up about custom properties

The demo assumes your HubSpot contact records have these custom properties:

```
policy_type, carrier, policy_premium,
policy_effective_date, policy_expiration_date, policy_number
```

If your agency uses different property names, override them via environment variables in the same Claude Desktop config. Example:

```json
"env": {
  "HUBSPOT_PRIVATE_APP_TOKEN": "pat-na1-...",
  "HS_PROP_POLICY_TYPE": "policy_line",
  "HS_PROP_CARRIER": "carrier_name",
  "HS_PROP_POLICY_PREMIUM": "annual_premium",
  "HS_PROP_POLICY_EXPIRATION": "renewal_date"
}
```

If a property doesn't exist on your contacts at all, the demo gracefully degrades — that contact just won't appear in renewal pipeline results, etc. Reach out if anything looks off.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Claude Desktop doesn't show the connector | Config file syntax error | Validate the JSON with `cat claude_desktop_config.json \| python -m json.tool` |
| Connector shows but tools error with "module not found" | Wrong Python path in config | Run `which python` inside your activated venv and use that exact path |
| Live mode returns 401 errors | Token wrong or expired | Regenerate the private app token in HubSpot |
| Live mode returns "property does not exist" | Custom property names different in your HubSpot | Set the `HS_PROP_*` env vars (see above) |
| Renewal pipeline is empty in live mode | No contacts with `policy_expiration_date` set | Verify a few test contacts have the date filled in |

If you hit anything not on this list, just reply to the email Anis sent.
