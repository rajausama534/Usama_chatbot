from __future__ import annotations

from core import operator_state


def operator_center(parameters=None, player=None, **kwargs) -> str:
    p = parameters or {}
    action = str(p.get("action", "dashboard")).strip().lower()

    if action in ("dashboard", "status"):
        text = operator_state.dashboard_text()
        if player is not None and hasattr(player, "show_content"):
            try:
                player.show_content("OPERATOR CENTER", text)
            except Exception:
                pass
        return text

    if action == "set_permission":
        return operator_state.set_permission_mode(p.get("mode", ""))

    if action == "recent":
        items = operator_state.recent(int(p.get("limit", 10) or 10))
        if not items:
            return "No recent actions."
        out = []
        for e in reversed(items):
            out.append(f"{'OK' if e.get('ok') else 'CHECK'} | {e.get('tool')} | {e.get('result','')[:120]}")
        return "\n".join(out)

    if action == "remember":
        return operator_state.remember_context(p.get("key", ""), p.get("value", ""))

    if action == "context":
        ctx = operator_state.context()
        return "\n".join(f"{k}: {v}" for k, v in ctx.items()) if ctx else "No operator context saved yet."

    return "Unknown operator_center action."


TOOL = {
    "name": "operator_center",
    "description": (
        "Usama's operator center: show the personal dashboard, change permission mode "
        "(read/assist/execute), inspect recent verified action receipts, and store short "
        "action context such as the current CRM owner/account/task."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "dashboard | status | set_permission | recent | remember | context"},
            "mode": {"type": "STRING", "description": "read | assist | execute"},
            "limit": {"type": "INTEGER", "description": "How many recent receipts to show"},
            "key": {"type": "STRING", "description": "Context key for remember"},
            "value": {"type": "STRING", "description": "Context value for remember"}
        },
        "required": ["action"]
    },
    "handler": operator_center,
}
