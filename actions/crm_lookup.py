"""Discovered Usama action: read existing CRM leads, owners and follow-ups.

Never performs a database mutation, never fetches unrestricted rows.
"""
import json
from core import crm_client

def crm_lookup(parameters):
    p = parameters or {}
    action = str(p.get("action", "")).strip().lower()
    try:
        if action == "lead":
            result = crm_client.find_leads(p.get("query", ""), p.get("limit", 10))
        elif action == "owner":
            result = crm_client.find_owners(p.get("query", ""), p.get("limit", 10))
        elif action == "followups":
            result = crm_client.followups(p.get("days", 7), p.get("limit", 20))
        else:
            return "Choose action 'lead', 'owner' or 'followups'."
        return json.dumps(result, ensure_ascii=False)
    except (RuntimeError, ValueError, KeyError) as exc:
        return f"CRM read unavailable: {exc}"

TOOL = {
    "name": "crm_lookup",
    "description": "Read-only lookup against the user's EXISTING Usama CRM Supabase project (leads, owner contacts or upcoming lead follow-ups). Never updates the CRM, sends messages, or schedules meetings. If not logged in ask user to run python3 -m core.crm_client login on their own Mac.",
    "parameters": {"type": "OBJECT", "properties": {
        "action": {"type": "STRING", "description": "lead, owner, followups"},
        "query": {"type": "STRING", "description": "Name to search when action is lead or owner"},
        "days": {"type": "INTEGER", "description": "For followups: future days, 0-30"},
        "limit": {"type": "INTEGER", "description": "Maximum results to return, 1-20"}
    }, "required": ["action"]},
    "handler": crm_lookup,
}
