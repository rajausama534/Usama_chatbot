"""Inspect an existing CRM lead without modifying CRM records.

Use CRM's authenticated Supabase client. This reads full details only for a
uniquely identified lead. It does not interact with page UI or claim to.
"""
from __future__ import annotations

import json
import re
from core import crm_client


def _detail(lead_id):
    value = str(lead_id or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value):
        raise ValueError("Invalid lead identifier.")
    return crm_client._get("leads", {"select": "*", "id": "eq." + value, "limit": "1"})


def crm_inspect(parameters):
    p = parameters or {}
    lead_id = p.get("lead_id")
    try:
        if lead_id:
            result = _detail(lead_id)
        else:
            query = str(p.get("query") or "").strip()
            matches = crm_client.find_leads(query, limit=5)
            if "error" in matches:
                return json.dumps(matches, ensure_ascii=False)
            rows = matches.get("records", [])
            if not rows:
                return "No matching CRM lead found. No records changed."
            if len(rows) != 1:
                return json.dumps({
                    "message": "Multiple leads matched. Ask which lead to inspect using the name and ID.",
                    "matches": [{"id": r.get("id"), "name": r.get("name"),
                                 "project_inquired": r.get("project_inquired")}
                                for r in rows],
                }, ensure_ascii=False)
            result = _detail(rows[0]["id"])
        if "error" in result:
            return json.dumps(result, ensure_ascii=False)
        rows = result.get("records", [])
        payload = {
            "website": crm_client.CRM_WEBSITE_URL,
            "read_only": True,
            "lead": rows[0] if rows else None,
            "message": "Lead details retrieved from existing CRM; no UI click or mutation performed."
                       if rows else "Lead not accessible or not found."
        }
        output = json.dumps(payload, ensure_ascii=False, default=str)
        if len(output) > 18000:
            return json.dumps({
                "read_only": True,
                "message": "Lead found, but the full record exceeds the safe response size. "
                           "Inspect this lead directly in the existing CRM.",
                "lead_id": (rows[0] or {}).get("id") if rows else None,
                "website": crm_client.CRM_WEBSITE_URL,
            }, ensure_ascii=False, default=str)
        return output
    except (ValueError, KeyError, RuntimeError) as exc:
        return "CRM inspection unavailable: " + str(exc)


TOOL = {
    "name": "crm_inspect",
    "description": "Find a lead in the EXISTING Usama CRM and read its full details, notes and follow-up fields where permitted. Searches a lead name or uses exact lead_id. A unique match is automatically inspected; ambiguous matches require selection. Read-only Supabase access; DOES NOT click inside a browser, update records or send messages. For visually inspecting the webpage use browser_control get_text or screenshot separately.",
    "parameters": {"type": "OBJECT", "properties": {
        "query": {"type": "STRING", "description": "Lead name to look up"},
        "lead_id": {"type": "STRING", "description": "Exact CRM lead ID if known"}
    }},
    "handler": crm_inspect,
}
