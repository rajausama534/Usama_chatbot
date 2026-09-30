"""
Dedicated browser workspaces for Gmail, CRM, Exness and Google Calendar.

The tool intentionally separates navigation/inspection from final consequential
clicks. The model focuses the real user's Chrome tab, reads the page with
screen_process, prepares the UI, then uses final_click only for the last
externally consequential action.
"""
from __future__ import annotations

import platform
import subprocess
import time

from core import confirm

try:
    import pyautogui
    pyautogui.FAILSAFE = True
except Exception:
    pyautogui = None

_TARGETS = {
    "gmail": ("Gmail", "https://mail.google.com/"),
    "calendar": ("Calendar", "https://calendar.google.com/"),
    "exness": ("Exness", "https://my.exness.com/"),
    "crm": ("CRM", ""),
}


def _run(script: str) -> tuple[bool, str]:
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=10)
    if r.returncode != 0:
        return False, (r.stderr or "AppleScript failed").strip()
    return True, (r.stdout or "").strip()


def _focus_or_open(workspace: str, query: str = "") -> str:
    if platform.system() != "Darwin":
        return "Dedicated existing-Chrome workspace control is currently supported on macOS."
    key = (workspace or "").strip().lower()
    title, default_url = _TARGETS.get(key, (workspace, ""))
    needle = (query or title or workspace).strip()
    safe = needle.replace("\\", "\\\\").replace('"', '\\"')
    script = f'''
tell application "Google Chrome"
    if not running then
        activate
    else
        repeat with wi from 1 to count of windows
            set w to window wi
            repeat with ti from 1 to count of tabs of w
                set t to tab ti of w
                ignoring case
                    if (title of t) contains "{safe}" or (URL of t) contains "{safe}" then
                        set active tab index of w to ti
                        set index of w to 1
                        activate
                        return "FOUND" & tab & (title of t) & tab & (URL of t)
                    end if
                end ignoring
            end repeat
        end repeat
    end if
    return "NOT_FOUND"
end tell
'''
    ok, out = _run(script)
    if ok and out.startswith("FOUND"):
        parts = out.split("\t")
        shown = parts[1] if len(parts) > 1 else title
        return (
            f"{title} workspace focused: {shown}. "
            "Next use screen_process to read the current page before acting."
        )
    if not default_url:
        return (
            f"No open Chrome tab matched {needle}. For CRM, call chrome_tabs list "
            "to identify the real CRM tab or ask for its URL once."
        )
    safe_url = default_url.replace('"', '\\"')
    open_script = f'''
tell application "Google Chrome"
    activate
    if not running then
        open location "{safe_url}"
    else
        tell front window
            make new tab with properties {{URL:"{safe_url}"}}
            set active tab index to count of tabs
        end tell
    end if
end tell
'''
    ok2, err = _run(open_script)
    return (
        f"Opened {title}. Next use screen_process to read the page."
        if ok2 else f"Could not open {title}: {err}"
    )


def _final_click(workspace: str, action_name: str, x: int, y: int) -> str:
    if pyautogui is None:
        return "PyAutoGUI is unavailable; final action was not performed."
    key = (workspace or "").lower().strip()
    action = (action_name or "").strip()
    if key == "gmail":
        title = f"Confirm Gmail action: {action}?"
    elif key == "exness":
        title = f"Confirm Exness action: {action}?"
    else:
        title = f"Confirm {workspace} action: {action}?"

    def _do():
        pyautogui.click(int(x), int(y))
        time.sleep(0.6)
        return f"Final {workspace} action clicked: {action}. Verify the result on screen before reporting success."

    return confirm.request(
        key=f"workspace:{key}:{action}:{x}:{y}",
        title=title,
        detail=f"Final action: {action}",
        run=_do,
    )


def service_workspace(parameters=None, player=None, **kwargs) -> str:
    p = parameters or {}
    workspace = str(p.get("workspace", "")).strip().lower()
    action = str(p.get("action", "open")).strip().lower()

    if workspace not in _TARGETS:
        return "Workspace must be gmail, crm, exness, or calendar."

    if action in ("open", "focus", "inspect"):
        return _focus_or_open(workspace, str(p.get("query", "")))

    if action == "final_click":
        try:
            x, y = int(p.get("x")), int(p.get("y"))
        except Exception:
            return "final_click requires x and y coordinates."
        return _final_click(workspace, str(p.get("action_name", "final action")), x, y)

    return "Unknown action. Use open/focus/inspect or final_click."


TOOL = {
    "name": "service_workspace",
    "description": (
        "Dedicated workspace controller for Gmail, CRM, Exness and Google Calendar in the user's real Chrome session. "
        "Use open/focus first, then screen_process to read the page. For Gmail send/delete and Exness trade place/close, "
        "use final_click only for the very last consequential click; it asks the user once for confirmation."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "workspace": {"type": "STRING", "description": "gmail | crm | exness | calendar"},
            "action": {"type": "STRING", "description": "open | focus | inspect | final_click"},
            "query": {"type": "STRING", "description": "Optional tab title or URL fragment, especially for CRM"},
            "action_name": {"type": "STRING", "description": "Human-readable final action, e.g. delete email, send email, place BUY 0.10 XAUUSD, close position"},
            "x": {"type": "INTEGER", "description": "Final button x coordinate"},
            "y": {"type": "INTEGER", "description": "Final button y coordinate"}
        },
        "required": ["workspace", "action"]
    },
    "handler": service_workspace,
}
