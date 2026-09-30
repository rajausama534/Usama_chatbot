"""
Read and switch the user's already-open Google Chrome tabs on macOS.

This does not create a separate Playwright profile. It talks to the user's
current Chrome windows through AppleScript, so CRM/Gmail/Exness tabs that are
already open can be found and focused.
"""
from __future__ import annotations

import platform
import subprocess


def _run(script: str) -> tuple[bool, str]:
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=10)
    if r.returncode != 0:
        return False, (r.stderr or "AppleScript failed").strip()
    return True, (r.stdout or "").strip()


def _list_tabs() -> str:
    if platform.system() != "Darwin":
        return "Existing Chrome tab inspection is currently supported on macOS."
    script = r'''
tell application "Google Chrome"
    if not running then return "CHROME_NOT_RUNNING"
    set outText to ""
    repeat with wi from 1 to count of windows
        set w to window wi
        repeat with ti from 1 to count of tabs of w
            set t to tab ti of w
            set outText to outText & wi & tab & ti & tab & (title of t) & tab & (URL of t) & linefeed
        end repeat
    end repeat
    return outText
end tell
'''
    ok, out = _run(script)
    if not ok:
        return f"Could not read Chrome tabs: {out}"
    if out == "CHROME_NOT_RUNNING":
        return "Google Chrome is not running."
    return out or "No Chrome tabs found."


def _focus_tab(query: str) -> str:
    q = (query or "").strip()
    if not q:
        return "Please specify a tab title, website name, or URL fragment."
    safe = q.replace("\\", "\\\\").replace('"', '\\"')
    script = f'''
tell application "Google Chrome"
    if not running then return "CHROME_NOT_RUNNING"
    set needle to "{safe}"
    repeat with wi from 1 to count of windows
        set w to window wi
        repeat with ti from 1 to count of tabs of w
            set t to tab ti of w
            set ttl to title of t
            set u to URL of t
            ignoring case
                if ttl contains needle or u contains needle then
                    set active tab index of w to ti
                    set index of w to 1
                    activate
                    return "FOUND" & tab & ttl & tab & u
                end if
            end ignoring
        end repeat
    end repeat
    return "NOT_FOUND"
end tell
'''
    ok, out = _run(script)
    if not ok:
        return f"Could not focus Chrome tab: {out}"
    if out == "CHROME_NOT_RUNNING":
        return "Google Chrome is not running."
    if out == "NOT_FOUND":
        return f"No open Chrome tab matched: {q}"
    parts = out.split("\t")
    if len(parts) >= 3 and parts[0] == "FOUND":
        return f"Focused Chrome tab: {parts[1]} — {parts[2]}"
    return out


def _open(query: str) -> str:
    q = (query or "").strip()
    if not q:
        return "Please specify a website or URL."
    if "://" not in q:
        if "." not in q:
            q = "https://www.google.com/search?q=" + q.replace(" ", "+")
        else:
            q = "https://" + q
    safe = q.replace("\\", "\\\\").replace('"', '\\"')
    script = f'''
tell application "Google Chrome"
    activate
    if not running then
        open location "{safe}"
        return "OPENED"
    end if
    tell front window
        make new tab with properties {{URL:"{safe}"}}
        set active tab index to count of tabs
    end tell
    return "OPENED"
end tell
'''
    ok, out = _run(script)
    return f"Opened in Chrome: {q}" if ok and out == "OPENED" else f"Could not open in Chrome: {out}"


def chrome_tabs(parameters=None, **kwargs) -> str:
    p = parameters or {}
    action = (p.get("action") or "").strip().lower()
    query = (p.get("query") or "").strip()

    if action == "list":
        return _list_tabs()
    if action in ("focus", "switch", "find"):
        return _focus_tab(query)
    if action == "open":
        return _open(query)
    return "Unknown chrome_tabs action. Use list, focus, or open."


TOOL = {
    "name": "chrome_tabs",
    "description": (
        "On macOS, inspect and control the user's already-open Google Chrome tabs. "
        "Use this when the user asks what tabs are open, asks to open/switch to CRM, Gmail, Exness, "
        "or another website already open in Chrome. Read-only listing/focusing does not require confirmation."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "list | focus | open"},
            "query": {"type": "STRING", "description": "Tab title, URL fragment, website name, or URL/search text"}
        },
        "required": ["action"]
    },
    "handler": chrome_tabs,
}
