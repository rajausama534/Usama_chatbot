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
    pyautogui.PAUSE = 0.05
except Exception:
    pyautogui = None

try:
    import pyperclip
except Exception:
    pyperclip = None

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




def _ensure_front_chrome() -> tuple[bool, str]:
    if platform.system() != "Darwin":
        return False, "Existing-session workspace control is only available on macOS."
    ok, out = _run(
        'tell application "System Events" to get name of first application process whose frontmost is true'
    )
    if not ok or "chrome" not in out.lower():
        return False, "Google Chrome is not the active application."
    return True, ""


def _intermediate_click(workspace: str, action_name: str, x: int, y: int) -> str:
    if pyautogui is None:
        return "PyAutoGUI is unavailable."
    ok, why = _ensure_front_chrome()
    if not ok:
        return why
    label = (action_name or "intermediate control").strip()
    low = label.casefold()
    # Consequential actions must never bypass the one final confirmation gate.
    blocked = ("place trade", "buy now", "sell now", "close position",
               "delete email", "send email", "confirm order")
    if any(b in low for b in blocked):
        return "This is a final consequential action; use final_click instead."
    pyautogui.click(int(x), int(y))
    time.sleep(0.35)
    return f"Clicked {label}. Read the screen again before the next step."


def _intermediate_type(workspace: str, field_name: str, text: str,
                       x: int | None = None, y: int | None = None,
                       clear_first: bool = True) -> str:
    if pyautogui is None:
        return "PyAutoGUI is unavailable."
    ok, why = _ensure_front_chrome()
    if not ok:
        return why
    if x is not None and y is not None:
        pyautogui.click(int(x), int(y))
        time.sleep(0.15)
    if clear_first:
        pyautogui.hotkey("command", "a")
        pyautogui.press("delete")
    value = str(text or "")
    if pyperclip is not None:
        pyperclip.copy(value)
        pyautogui.hotkey("command", "v")
    else:
        pyautogui.write(value, interval=0.01)
    time.sleep(0.25)
    return f"Entered {field_name or 'value'}. Read the screen again before continuing."


def _press_key(key: str) -> str:
    if pyautogui is None:
        return "PyAutoGUI is unavailable."
    ok, why = _ensure_front_chrome()
    if not ok:
        return why
    k = (key or "").strip().lower()
    if not k:
        return "Key is required."
    pyautogui.press(k)
    time.sleep(0.2)
    return f"Pressed {k}. Read the screen again before continuing."


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

    if action == "click":
        try:
            x, y = int(p.get("x")), int(p.get("y"))
        except Exception:
            return "click requires x and y coordinates."
        return _intermediate_click(workspace, str(p.get("action_name", "control")), x, y)

    if action == "type":
        try:
            x = int(p.get("x")) if p.get("x") is not None else None
            y = int(p.get("y")) if p.get("y") is not None else None
        except Exception:
            return "type x/y coordinates must be integers when supplied."
        return _intermediate_type(
            workspace,
            str(p.get("field_name", "")),
            str(p.get("text", "")),
            x,
            y,
            bool(p.get("clear_first", True)),
        )

    if action == "press":
        return _press_key(str(p.get("key", "")))

    if action == "final_click":
        try:
            x, y = int(p.get("x")), int(p.get("y"))
        except Exception:
            return "final_click requires x and y coordinates."
        return _final_click(workspace, str(p.get("action_name", "final action")), x, y)

    return "Unknown action. Use open/focus/inspect/click/type/press/final_click."


TOOL = {
    "name": "service_workspace",
    "description": (
        "Dedicated workspace controller for Gmail, CRM, Exness and Google Calendar in the user's real Chrome session. "
        "Use open/focus first, then screen_process to read the page. For Gmail send/delete and Exness trade place/close, "
        "use click/type/press for intermediate controls, re-read the screen after every step, and use final_click only for the very last consequential click; it asks the user once for confirmation."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "workspace": {"type": "STRING", "description": "gmail | crm | exness | calendar"},
            "action": {"type": "STRING", "description": "open | focus | inspect | click | type | press | final_click"},
            "query": {"type": "STRING", "description": "Optional tab title or URL fragment, especially for CRM"},
            "action_name": {"type": "STRING", "description": "Human-readable control/action name"},
            "field_name": {"type": "STRING", "description": "Field being edited, e.g. lot size, stop loss, take profit"},
            "text": {"type": "STRING", "description": "Text/value for type action"},
            "key": {"type": "STRING", "description": "Key for press action, e.g. escape, enter"},
            "clear_first": {"type": "BOOLEAN", "description": "Clear field before typing, default true"},
            "x": {"type": "INTEGER", "description": "Screen x coordinate when needed"},
            "y": {"type": "INTEGER", "description": "Screen y coordinate when needed"}
        },
        "required": ["workspace", "action"]
    },
    "handler": service_workspace,
}
