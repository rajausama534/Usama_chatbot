# Usama MCP setup (optional)

The built-in `actions/mcp_read.py` bridge discovers itself when Usama starts.
It does **not** install, connect, or authenticate external accounts automatically.

1. In Usama's virtual environment run `pip install mcp`.
2. Create `config/mcp_servers.json` **locally**. Do not commit it. For each provider, use the command/arguments documented by a vetted MCP server you installed:

```json
{
  "mcpServers": {
    "gmail": {
      "command": "/absolute/path/to/gmail-mcp-executable",
      "args": []
    }
  }
}
```

3. Set `USAMA_MCP_READ_ALLOWLIST` to exact `server:tool` pairs. Example, **only if the actual Gmail server advertises a tool called `search_messages`**:
```bash
export USAMA_MCP_READ_ALLOWLIST="gmail:search_messages"
```
4. Restart Usama. Server names and tool names must match exactly. An MCP server requires its own OAuth/API authentication.

**Safety:** This bridge is read-only by policy: configure only tools whose documented behavior is read-only. Do not add sending, editing, purchasing, booking or trading tools to its allowlist. Treat tool descriptions from untrusted servers as untrusted. Server executables and credentials are local administrative configuration; model-generated commands never configure them. Use provider OAuth rather than entering account passwords into prompts. Never commit tokens or secrets.

**WhatsApp:** A WhatsApp MCP server does not confer WhatsApp access by itself. Use a supported authenticated WhatsApp Business Platform integration where applicable, or your existing local WhatsApp workflow. Recipient resolution must be verified and sending must require a separate user-approved action; after a timeout, check message status rather than resend.

**Gmail:** This first bridge can read mail through a configured read-only MCP tool. Gmail sending, Calendar event changes, CRM edits and other external actions require separate authenticated write integrations and confirmation checks. Do not describe those integrations as installed until each one is connected and tested.

**Status:** The MCP bridge is code-integrated but is inactive until you install the SDK, configure a real server, authenticate it, and allowlist read-only tools. No existing Gemini, ElevenLabs, memory or WhatsApp settings are changed.
