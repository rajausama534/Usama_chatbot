# Usama integration setup and evening test

Existing `actions/mcp_read.py` is the **read-only MCP bridge** for reviewed tool names. `integration_status` reports all seven services: WhatsApp, Gmail, Calendar, Contacts, Browser, Supabase CRM, Shopify. A configured server is **not** a verified connection.

## Mac preparation

```bash
cd ~/Usama_chatbot
git pull --ff-only origin main
source .venv/bin/activate
pip install mcp
python3 -m unittest discover -s tests
```

Copy `config/mcp_servers.example.json` to **local** `config/mcp_servers.json`; substitute each placeholder with the actual command and arguments published by your chosen vetted MCP provider. Never commit `config/mcp_servers.json`, passwords or API tokens. Obtain OAuth/account permissions locally. For browser control use the existing Playwright integration rather than introducing an unreviewed server. Some WhatsApp integrations use a local authenticated client instead of MCP; do not bypass the provider's login/security requirements.

For each installed server, inspect its advertised tools, verify the account, and explicitly set only **read-only** entries in `USAMA_MCP_READ_ALLOWLIST` as comma-separated `server:tool` pairs. No wildcard. An example shape (not a real tool): `gmail:ACTUAL_READ_TOOL_NAME,supabase:ACTUAL_READ_TOOL_NAME`. Launch Usama and ask it for `integration_status`. Then perform a harmless Gmail search, a calendar read, a contacts lookup, a test browser navigation, a permission-scoped CRM record read, a Shopify product read, and a WhatsApp contact lookup if your vetted integration supports it. Confirm each result against the provider's actual data.

## CRM and outbound automation boundaries

Use the **existing Supabase project** behind the Vercel CRM. First review its schema, access policies and ownership fields; use least-privilege credentials. Do not create a new CRM or alter production tables on the strength of this bridge. Automated follow-ups, reminders and meeting booking require separate, explicitly approved write operations, scheduling, deduplication, per-contact permission checks and end-to-end tests. Outbound WhatsApp/Gmail must check the exact recipient and message; uncertain send results must not trigger a blind retry. Shopify product/order edits likewise require separate scoped write actions. This preparation does **not** claim those actions or live connections are complete.

Gemini voice and ElevenLabs are independent of MCP setup. No voice-provider switch is made by these changes.

## Updated bridge verification

The local MCP configuration is ignored by Git (.gitignore now excludes `config/mcp_servers.json`). After installing the SDK and authenticating a reviewed **stdio** server, ask Usama to call `mcp_discover` with that server name to see the actual advertised tools. Then explicitly allowlist only reviewed read operations; `mcp_read` accepts `arguments_json` for tool-specific structured arguments. The bridge refuses tools explicitly marked non-read-only and blocks common mutating operation names. Do not treat this as a guarantee for maliciously mislabeled third-party servers: choose a trusted provider and read-only credentials.

Run offline regressions with `python3 -m unittest discover -s tests`. These tests do not authenticate or verify live provider functionality. The Supabase project currently visible through the connected account is INACTIVE, so first identify the actual production CRM project in your own Supabase dashboard before enabling CRM access. We have not restored or changed any database.
