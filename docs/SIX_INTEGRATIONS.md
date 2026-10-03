# Six integrations: activation checklist

The existing `actions/mcp_read.py` bridge can access **reviewed read-only** MCP tools only when their servers are configured locally. `actions/integration_status.py` reports readiness; **configured does not mean connected**. Keep `config/mcp_servers.json` local and out of Git.

| Service | Connection | First verification | Write safety |
| --- | --- | --- | --- |
| WhatsApp | A vetted WhatsApp MCP server with supported authentication, or existing authenticated local WhatsApp workflow | Identify the exact contact and read a test conversation | Confirm recipient and message before sending; check status after timeout, never blindly resend |
| Gmail | OAuth-authenticated Gmail MCP server | Search inbox for a harmless test subject | Sending must use a separate approved write action |
| Calendar | OAuth-authenticated Google Calendar MCP server | Read upcoming events | Show event details and confirm before creating/updating/deleting |
| Contacts | OAuth-authenticated Google Contacts MCP server | Search for a chosen saved contact | Use exact contact ID and require confirmation on edits |
| Browser | Existing local Playwright integration (MCP optional) | Open a permitted test page in the selected browser | Do not reuse logins without explicit permission or bypass access checks |
| Supabase | Authenticated, least-privilege Supabase MCP server | Read a sample CRM record with access controls | CRM changes require explicit action and verify the affected record |

Local preparation on Mac:

```bash
cd ~/Usama_chatbot
git pull --ff-only origin main
source .venv/bin/activate
pip install mcp
```

Install vetted servers for WhatsApp, Gmail, Calendar, Contacts, and Supabase from their provider's current documentation. Put **their actual executable commands** in your local `config/mcp_servers.json`. Do not copy imaginary endpoints, use fake tokens, or upload credentials to GitHub. You can configure these as named `mcpServers`: `whatsapp`, `gmail`, `calendar`, `contacts`, `supabase`. Browser uses your existing Playwright package and does not require an extra MCP server. Then explicitly set `USAMA_MCP_READ_ALLOWLIST` to reviewed server/tool pairs documented by those installed servers. The read bridge is opt-in, not an account connection.

When you are home, authorize each provider on your own machine through its supported OAuth/login flow. Test read operations first. Message sending and CRM writes should only be added as separate confirmation-gated actions after account authentication and destination verification. Voice, Gemini, ElevenLabs and existing user data are unchanged by these additions.
