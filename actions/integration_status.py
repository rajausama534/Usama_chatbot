"""Local integration readiness check. Configuration never proves authentication."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVICES = ("whatsapp", "gmail", "calendar", "contacts", "browser", "supabase", "shopify")

def integration_status(parameters):
    path = ROOT / "config" / "mcp_servers.json"
    try:
        configured = json.loads(path.read_text(encoding="utf-8")).get("mcpServers", {}) if path.exists() else {}
        if not isinstance(configured, dict):
            configured = {}
    except (OSError, ValueError):
        configured = {}
    sdk = importlib.util.find_spec("mcp") is not None
    result = {}
    for name in SERVICES:
        if name == "browser":
            result[name] = ("local Playwright installed; browser permission and live operation unverified"
                            if importlib.util.find_spec("playwright") else "install Playwright and authorize browser")
            continue
        details = configured.get(name)
        if isinstance(details, dict) and details.get("command") and sdk:
            result[name] = "server configured; authentication and live connection unverified"
        elif isinstance(details, dict) and details.get("command"):
            result[name] = "server configured; install mcp SDK; authentication unverified"
        else:
            result[name] = "not configured"
    return json.dumps(result, ensure_ascii=False)

TOOL = {
    "name": "integration_status",
    "description": "Show local readiness of WhatsApp, Gmail, Calendar, Contacts, browser, Supabase CRM and Shopify. Configuration does not prove authentication or execution.",
    "parameters": {"type": "OBJECT", "properties": {}},
    "handler": integration_status,
}
