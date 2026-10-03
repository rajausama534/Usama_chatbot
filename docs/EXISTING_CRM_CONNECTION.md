# Connect your EXISTING Vercel + Supabase CRM to Usama

Verified source: `rajausama534/usama-crm` (existing GitHub CRM frontend) points to `https://vnydxkmhrcesdffpfjpc.supabase.co`. This is **not** the inactive Supabase project currently visible to the separate ChatGPT Supabase connector. No database schema, records, Vercel deployment or CRM frontend were changed.

The assistant now includes:
- `actions/crm_lookup.py`: direct **read-only** Usama action for lead searches, owner searches and upcoming lead follow-ups.
- `core/crm_client.py`: narrow HTTPS client with your CRM's existing public project URL/publishable key. It uses a user-authenticated Supabase session, respects your existing row-level policies and reads only the `leads` and `owners` tables.
- `core/crm_mcp_server.py`: local stdio MCP server exposing `search_leads`, `search_owners`, `upcoming_followups` (all read-only).

## One-time local Mac login

From your Mac's Terminal (not ChatGPT), run:

```bash
cd ~/Usama_chatbot
git pull --ff-only origin main
source .venv/bin/activate
pip install -r requirements.txt
python3 -m unittest discover -s tests
python3 -m core.crm_client login
```

Enter the **existing CRM login email and password only in your own Terminal**. The password is not saved. The refresh token goes into the local OS keychain using `keyring`; never paste passwords/tokens here or into GitHub. If the existing CRM uses Google-only login rather than email/password, this login method won't work and we must add the correct OAuth flow; do not create a new CRM account.

Restart Usama with `python3 main.py`. Ask: "Find lead John in my CRM", "Find owner Ali", or "Show CRM follow-ups for the next seven days". Usama's `crm_lookup` action runs in read-only mode and will report a permission/authentication error rather than silently changing records.

## MCP connection (optional, direct action above works without MCP setup)

Your new dedicated MCP server can also be connected as a stdio server. In your **local ignored** `config/mcp_servers.json`, add:

```json
{
  "mcpServers": {
    "crm": {
      "command": "/Users/YOUR_MAC_USER/Usama_chatbot/.venv/bin/python3",
      "args": ["-m", "core.crm_mcp_server"]
    }
  }
}
```

Replace `YOUR_MAC_USER` with your own home folder name; keep any other existing entries. Launch Usama from `~/Usama_chatbot` so its working directory resolves `core`. Set the read-only tool allowlist in the same Mac terminal **before** starting Usama:

```bash
export USAMA_MCP_READ_ALLOWLIST="crm:search_leads,crm:search_owners,crm:upcoming_followups"
```

Run `integration_status` and `mcp_discover` with server `crm`, then use `mcp_read` for an allowlisted operation. The `integration_status` action's `supabase` row tracks a separately named generic server and does not automatically certify this dedicated `crm` connection.

## Not enabled yet

Automated WhatsApp follow-ups, editing lead statuses, writing meeting events, scheduled reminders and CRM mutations are **not** part of this read-only bridge. First verify the real account, live data, permissions and user-approved outbound workflow. No service-role/secret key is used, and no database migration is required. Disconnect locally with `python3 -m core.crm_client logout`.
