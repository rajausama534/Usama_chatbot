"""
Persistent operator state for Usama.

Provides:
- action memory (recent tools, targets and outcomes)
- permission modes: read / assist / execute
- verified action receipts
- lightweight task history for the personal dashboard
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_PATH = _BASE / "memory" / "operator_state.json"
_LOCK = threading.Lock()
_MAX_EVENTS = 120

_DEFAULT = {
    "permission_mode": "execute",
    "events": [],
    "context": {},
}


def _load() -> dict:
    try:
        data = json.loads(_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return dict(_DEFAULT)
        data.setdefault("permission_mode", "execute")
        data.setdefault("events", [])
        data.setdefault("context", {})
        return data
    except Exception:
        return {"permission_mode": "execute", "events": [], "context": {}}


def _save(data: dict) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(_PATH)


def get_permission_mode() -> str:
    mode = str(_load().get("permission_mode", "execute")).lower()
    return mode if mode in {"read", "assist", "execute"} else "execute"


def set_permission_mode(mode: str) -> str:
    mode = str(mode or "").strip().lower()
    if mode not in {"read", "assist", "execute"}:
        return "Permission mode must be read, assist, or execute."
    with _LOCK:
        d = _load()
        d["permission_mode"] = mode
        _save(d)
    return f"Permission mode set to {mode}."


def _looks_high_risk(tool: str, args: dict) -> bool:
    name = (tool or "").lower()
    action = str((args or {}).get("action", "")).lower()
    joined = " ".join([name, action, str((args or {}).get("operation", "")).lower()])
    words = (
        "send_message", "delete", "remove", "trash", "shutdown", "restart",
        "trade", "order", "buy", "sell", "close_position", "place_order",
        "transfer", "payment", "purchase", "submit"
    )
    return any(w in joined for w in words)


def _looks_mutating(tool: str, args: dict) -> bool:
    name = (tool or "").lower()
    action = str((args or {}).get("action", "")).lower()
    readish = {
        "get", "read", "list", "search", "find", "status", "screenshot",
        "screen_find", "copy", "get_text", "get_url", "recall", "open",
        "focus", "switch", "go_to"
    }
    if action in readish:
        return False
    if any(k in name for k in ("search", "status", "screen_process", "recall", "web_search")):
        return False
    return _looks_high_risk(tool, args) or action in {
        "type", "smart_type", "click", "double_click", "right_click", "paste",
        "fill_form", "smart_click", "press", "move", "drag", "create", "write",
        "rename", "copy_file", "move_file"
    }


def allow_tool(tool: str, args: dict) -> tuple[bool, str]:
    mode = get_permission_mode()
    if mode == "execute":
        return True, ""
    if mode == "read" and _looks_mutating(tool, args):
        return False, f"Permission mode is READ. '{tool}' is blocked because it can change something."
    if mode == "assist" and _looks_high_risk(tool, args):
        return False, f"Permission mode is ASSIST. Final high-risk action '{tool}' is blocked."
    return True, ""


def record_action(tool: str, args: dict, result: str) -> None:
    try:
        txt = str(result or "")
        low = txt.lower()
        ok = not any(x in low for x in (
            "failed", "error", "not sent", "could not", "blocked", "unknown tool"
        ))
        event = {
            "time": int(time.time()),
            "tool": str(tool or ""),
            "args": dict(args or {}),
            "result": txt[:700],
            "ok": bool(ok),
        }
        with _LOCK:
            d = _load()
            events = list(d.get("events", []))
            events.append(event)
            d["events"] = events[-_MAX_EVENTS:]
            ctx = dict(d.get("context", {}))
            ctx["last_tool"] = event["tool"]
            ctx["last_args"] = event["args"]
            ctx["last_result"] = event["result"]
            ctx["last_ok"] = event["ok"]
            d["context"] = ctx
            _save(d)
    except Exception:
        pass


def remember_context(key: str, value) -> str:
    key = str(key or "").strip()
    if not key:
        return "Context key is empty."
    with _LOCK:
        d = _load()
        ctx = dict(d.get("context", {}))
        ctx[key] = value
        d["context"] = ctx
        _save(d)
    return f"Remembered {key}."


def recent(limit: int = 12) -> list[dict]:
    d = _load()
    return list(d.get("events", []))[-max(1, min(int(limit), 50)):]


def context() -> dict:
    return dict(_load().get("context", {}))


def dashboard_text() -> str:
    mode = get_permission_mode().upper()
    events = recent(12)
    ok = sum(1 for e in events if e.get("ok"))
    fail = len(events) - ok
    lines = [
        "USAMA // OPERATOR CENTER",
        f"Permission: {mode}",
        f"Recent verified actions: {len(events)}  |  Success: {ok}  |  Needs attention: {fail}",
        "",
        "RECENT ACTIVITY",
    ]
    if not events:
        lines.append("No actions recorded yet.")
    else:
        for e in reversed(events[-8:]):
            mark = "OK" if e.get("ok") else "CHECK"
            target = ""
            a = e.get("args") or {}
            for k in ("receiver", "query", "app_name", "url", "file_path", "path"):
                if a.get(k):
                    target = f" — {str(a[k])[:44]}"
                    break
            lines.append(f"[{mark}] {e.get('tool','')}{target}")

    lines += [
        "",
        "CONTROL MODES",
        "READ — inspect/search only",
        "ASSIST — prepare changes, block final high-risk actions",
        "EXECUTE — perform actions; individual high-risk tools still use their final confirmation gates",
        "",
        "LIVE SECTIONS",
        "Mail / CRM / trading items appear here as those actions are read or executed.",
    ]
    return "\n".join(lines)
