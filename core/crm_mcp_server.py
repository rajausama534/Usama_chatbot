"""Read-only MCP stdio server for existing Usama CRM.

Start from the project root: python3 -m core.crm_mcp_server
Requires: pip install mcp requests keyring
Authenticate once locally first: python3 -m core.crm_client login
"""
import json
from mcp.server.fastmcp import FastMCP
from core import crm_client
from actions.crm_inspect import crm_inspect

mcp = FastMCP("usama-existing-crm")

@mcp.tool()
def search_leads(name: str, limit: int = 10) -> str:
    """Read-only: search existing CRM leads by name."""
    return json.dumps(crm_client.find_leads(name, limit), ensure_ascii=False)

@mcp.tool()
def search_owners(name: str, limit: int = 10) -> str:
    """Read-only: search existing CRM property owners by name."""
    return json.dumps(crm_client.find_owners(name, limit), ensure_ascii=False)

@mcp.tool()
def inspect_lead(name: str = "", lead_id: str = "") -> str:
    """Read-only: inspect a unique existing lead by name or exact lead ID."""
    return crm_inspect({"query": name, "lead_id": lead_id})


@mcp.tool()
def upcoming_followups(days: int = 7, limit: int = 20) -> str:
    """Read-only: show scheduled lead follow-ups in the existing CRM."""
    return json.dumps(crm_client.followups(days, limit), ensure_ascii=False)

if __name__ == "__main__":
    mcp.run(transport="stdio")
