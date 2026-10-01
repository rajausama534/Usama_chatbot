from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_DATA_DIR = Path.home() / ".usama" / "visa_monitor"
_CONFIG = _DATA_DIR / "config.json"
_STATE = _DATA_DIR / "state.json"
_LABEL = "com.usama.visa-monitor"
_PLIST = Path.home() / "Library" / "LaunchAgents" / f"{_LABEL}.plist"

_DATE_PATTERNS = (
    r"\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b",
    r"\b(\d{1,2})[-/](\d{1,2})[-/](20\d{2})\b",
)
_MONTHS = {
    "january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
    "july":7,"august":8,"september":9,"october":10,"november":11,"december":12,
    "jan":1,"feb":2,"mar":3,"apr":4,"jun":6,"jul":7,"aug":8,"sep":9,
    "sept":9,"oct":10,"nov":11,"dec":12,
}


def _ensure_dir() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load(path: Path, default):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data
    except Exception:
        return default


def _save(path: Path, data) -> None:
    _ensure_dir()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _run_applescript(script: str, timeout: int = 15) -> tuple[bool, str]:
    try:
        r = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=timeout,
        )
        if r.returncode != 0:
            return False, (r.stderr or r.stdout or "AppleScript failed").strip()
        return True, (r.stdout or "").strip()
    except Exception as e:
        return False, str(e)


def _notify(title: str, message: str) -> None:
    if platform.system() != "Darwin":
        return
    t = str(title).replace("\\", "").replace('"', "'")
    m = str(message).replace("\\", "").replace('"', "'")
    _run_applescript(f'display notification "{m}" with title "{t}"')


def _list_chrome_tabs() -> list[dict]:
    if platform.system() != "Darwin":
        return []
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
    ok, out = _run_applescript(script)
    if not ok or out == "CHROME_NOT_RUNNING":
        return []
    rows = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 4:
            try:
                rows.append({"window": int(parts[0]), "tab": int(parts[1]),
                             "title": parts[2], "url": parts[3]})
            except Exception:
                pass
    return rows


def _looks_like_visa_tab(row: dict) -> bool:
    hay = f"{row.get('title','')} {row.get('url','')}".lower()
    keys = (
        "visa", "appointment", "ais.usvisa-info", "ustraveldocs",
        "usvisaappt", "cgi federal", "us travel docs",
    )
    return any(k in hay for k in keys)


def _resolve_tab(preferred_url: str = "") -> dict | None:
    tabs = _list_chrome_tabs()
    if not tabs:
        return None
    p = (preferred_url or "").strip().lower()
    if p:
        for row in tabs:
            if p == str(row.get("url", "")).strip().lower():
                return row
        # URL may redirect after login; domain/path fragment match is acceptable.
        p_no_q = p.split("?", 1)[0].rstrip("/")
        for row in tabs:
            u = str(row.get("url", "")).strip().lower()
            if p_no_q and (p_no_q in u or u.split("?",1)[0].rstrip("/") in p_no_q):
                return row
    for row in tabs:
        if _looks_like_visa_tab(row):
            return row
    return None


def _read_tab_text(row: dict) -> tuple[bool, str]:
    wi, ti = int(row["window"]), int(row["tab"])
    # Chrome requires View > Developer > Allow JavaScript from Apple Events.
    script = f'''
tell application "Google Chrome"
    if not running then return "CHROME_NOT_RUNNING"
    set t to tab {ti} of window {wi}
    try
        set bodyText to execute t javascript "document.body ? document.body.innerText : ''"
        return bodyText
    on error errText
        return "JS_ERROR:" & errText
    end try
end tell
'''
    ok, out = _run_applescript(script, timeout=20)
    if not ok:
        return False, out
    if out.startswith("JS_ERROR:"):
        return False, out
    return True, out


def _reload_tab(row: dict) -> None:
    wi, ti = int(row["window"]), int(row["tab"])
    script = f'''
tell application "Google Chrome"
    if running then
        tell tab {ti} of window {wi} to reload
    end if
end tell
'''
    _run_applescript(script)


def _parse_date_text(value: str) -> datetime | None:
    v = " ".join(str(value or "").strip().split())
    if not v:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%m-%d-%Y",
                "%B %d %Y", "%B %d, %Y", "%d %B %Y", "%b %d %Y",
                "%b %d, %Y", "%d %b %Y"):
        try:
            return datetime.strptime(v, fmt)
        except ValueError:
            pass
    return None


def _extract_dates(text: str) -> list[datetime]:
    found: set[datetime] = set()
    raw = text or ""
    for pat in _DATE_PATTERNS:
        for m in re.finditer(pat, raw):
            a,b,c = m.groups()
            try:
                if len(a) == 4:
                    dt = datetime(int(a), int(b), int(c))
                else:
                    # Numeric ambiguity: prefer day/month unless first number >12
                    x,y,yr = int(a), int(b), int(c)
                    if x > 12:
                        dt = datetime(yr, y, x)
                    elif y > 12:
                        dt = datetime(yr, x, y)
                    else:
                        dt = datetime(yr, y, x)
                found.add(dt)
            except Exception:
                pass

    month_alt = "|".join(sorted(_MONTHS, key=len, reverse=True))
    for m in re.finditer(
        rf"\b({month_alt})\s+(\d{{1,2}})(?:st|nd|rd|th)?[,]?\s+(20\d{{2}})\b",
        raw, flags=re.I,
    ):
        try:
            found.add(datetime(int(m.group(3)), _MONTHS[m.group(1).lower()], int(m.group(2))))
        except Exception:
            pass
    for m in re.finditer(
        rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({month_alt})[,]?\s+(20\d{{2}})\b",
        raw, flags=re.I,
    ):
        try:
            found.add(datetime(int(m.group(3)), _MONTHS[m.group(2).lower()], int(m.group(1))))
        except Exception:
            pass
    # Appointment portals can contain unrelated old dates. Keep a practical future window.
    now = datetime.now()
    return sorted(d for d in found if now.date() <= d.date() and d.year <= now.year + 3)


def _classify_page(text: str) -> str:
    low = (text or "").lower()
    if any(k in low for k in ("captcha", "verify you are human", "security verification")):
        return "verification"
    if any(k in low for k in ("sign in", "log in", "login", "password")) and not any(
        k in low for k in ("schedule appointment", "reschedule", "appointment date")
    ):
        return "login"
    return "ok"


def _install_launch_agent() -> tuple[bool, str]:
    if platform.system() != "Darwin":
        return False, "Visa background watcher currently supports macOS."
    _ensure_dir()
    _PLIST.parent.mkdir(parents=True, exist_ok=True)
    python_exe = str(Path(sys.executable).resolve())
    script_path = str(Path(__file__).resolve())
    plist = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>{_LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>{python_exe}</string>
    <string>{script_path}</string>
    <string>--check</string>
  </array>
  <key>StartInterval</key><integer>300</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>{_DATA_DIR / "monitor.log"}</string>
  <key>StandardErrorPath</key><string>{_DATA_DIR / "monitor.err.log"}</string>
</dict>
</plist>
'''
    _PLIST.write_text(plist, encoding="utf-8")
    subprocess.run(["launchctl", "unload", str(_PLIST)], capture_output=True, text=True)
    r = subprocess.run(["launchctl", "load", str(_PLIST)], capture_output=True, text=True)
    if r.returncode != 0:
        return False, (r.stderr or r.stdout or "launchctl failed").strip()
    return True, "installed"


def _remove_launch_agent() -> None:
    try:
        subprocess.run(["launchctl", "unload", str(_PLIST)], capture_output=True, text=True)
    except Exception:
        pass
    try:
        _PLIST.unlink(missing_ok=True)
    except Exception:
        pass


def check_once(notify: bool = True) -> dict:
    cfg = _load(_CONFIG, {})
    if not cfg.get("enabled"):
        return {"status": "disabled"}

    tab = _resolve_tab(cfg.get("url", ""))
    if not tab:
        result = {"status": "tab_missing", "message": "Visa appointment tab is not open in Chrome."}
        if notify:
            _notify("Usama Visa Monitor", result["message"])
        return result

    # Save redirected URL so later checks keep finding the authenticated page.
    if tab.get("url") and tab.get("url") != cfg.get("url"):
        cfg["url"] = tab["url"]
        _save(_CONFIG, cfg)

    _reload_tab(tab)
    # The launch job is infrequent; a short wait is acceptable and does not affect Usama voice latency.
    import time
    time.sleep(4)
    tab = _resolve_tab(cfg.get("url", "")) or tab
    ok, text = _read_tab_text(tab)
    if not ok:
        msg = (
            "Visa page could not be read. In Chrome enable View > Developer > "
            "Allow JavaScript from Apple Events, then monitoring can continue."
            if "javascript" in text.lower() or "apple events" in text.lower()
            else f"Visa page could not be read: {text[:180]}"
        )
        result = {"status": "read_error", "message": msg}
        if notify:
            _notify("Usama Visa Monitor", msg)
        return result

    page_state = _classify_page(text)
    if page_state in ("login", "verification"):
        msg = ("Visa portal needs login again." if page_state == "login"
               else "Visa portal needs CAPTCHA/security verification.")
        result = {"status": page_state, "message": msg}
        state = _load(_STATE, {})
        if state.get("last_alert") != page_state and notify:
            _notify("Usama Visa Monitor", msg)
        state["last_alert"] = page_state
        state["last_check"] = datetime.now().isoformat(timespec="seconds")
        _save(_STATE, state)
        return result

    dates = _extract_dates(text)
    baseline = _parse_date_text(cfg.get("current_appointment", ""))
    state = _load(_STATE, {})
    earliest = dates[0] if dates else None
    previous = _parse_date_text(state.get("earliest_seen", ""))

    result = {
        "status": "ok",
        "earliest": earliest.strftime("%Y-%m-%d") if earliest else "",
        "baseline": baseline.strftime("%Y-%m-%d") if baseline else "",
    }

    improved = False
    if earliest:
        if baseline and earliest < baseline:
            improved = True
        elif not baseline and previous and earliest < previous:
            improved = True

    if improved:
        msg = f"Earlier US visa appointment found: {earliest.strftime('%d %B %Y')}. Book it quickly."
        result.update({"status": "earlier_slot", "message": msg})
        key = earliest.strftime("%Y-%m-%d")
        if state.get("last_notified_slot") != key and notify:
            _notify("US Visa Slot Available", msg)
            state["last_notified_slot"] = key

    if earliest:
        state["earliest_seen"] = earliest.strftime("%Y-%m-%d")
    state["last_alert"] = result["status"]
    state["last_check"] = datetime.now().isoformat(timespec="seconds")
    _save(_STATE, state)
    return result


def visa_monitor(parameters=None, player=None, **kwargs) -> str:
    p = parameters or {}
    action = str(p.get("action", "status")).strip().lower()

    if action == "start":
        current = str(p.get("current_appointment", "")).strip()
        if current and not _parse_date_text(current):
            return "Current appointment date could not be parsed. Use YYYY-MM-DD or a clear date such as 2 February 2027."
        tab = _resolve_tab(str(p.get("url", "")).strip())
        if not tab:
            return (
                "Open the logged-in US visa appointment page in Chrome first. "
                "I will attach monitoring to that exact tab and session."
            )
        cfg = {
            "enabled": True,
            "url": tab.get("url", ""),
            "title": tab.get("title", ""),
            "current_appointment": current,
            "interval_seconds": 300,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        _save(_CONFIG, cfg)
        ok, why = _install_launch_agent()
        if not ok:
            return f"Visa monitor config was saved, but the 5-minute background job could not be installed: {why}"
        first = check_once(notify=False)
        if first.get("status") == "read_error":
            return first.get("message", "Visa monitor installed but page reading needs attention.")
        return (
            "US visa monitor is active every 5 minutes using the existing logged-in Chrome tab. "
            "It will alert on an earlier slot, login expiry, or CAPTCHA/security verification."
        )

    if action == "stop":
        cfg = _load(_CONFIG, {})
        cfg["enabled"] = False
        _save(_CONFIG, cfg)
        _remove_launch_agent()
        return "US visa monitor stopped."

    if action == "check":
        r = check_once(notify=False)
        if r.get("status") == "earlier_slot":
            return r.get("message", "Earlier visa slot found.")
        if r.get("status") in ("login", "verification", "read_error", "tab_missing"):
            return r.get("message", r.get("status", "Visa monitor needs attention."))
        if r.get("status") == "ok":
            e = r.get("earliest") or "no date detected"
            b = r.get("baseline") or "no baseline"
            return f"Visa monitor check complete. Earliest detected: {e}. Current appointment baseline: {b}."
        return f"Visa monitor status: {r.get('status','unknown')}."

    if action == "status":
        cfg = _load(_CONFIG, {})
        if not cfg.get("enabled"):
            return "US visa monitor is not active."
        st = _load(_STATE, {})
        return (
            f"US visa monitor active every 5 minutes. "
            f"Current appointment: {cfg.get('current_appointment') or 'not set'}. "
            f"Last earliest seen: {st.get('earliest_seen') or 'none'}. "
            f"Last check: {st.get('last_check') or 'not yet'}."
        )

    return "Unknown visa monitor action. Use start, stop, check, or status."


TOOL = {
    "name": "visa_monitor",
    "description": (
        "Manage the persistent US visa appointment watcher on macOS. It attaches to the user's "
        "existing logged-in Chrome visa appointment tab and checks every 5 minutes using a "
        "LaunchAgent, so monitoring is independent of the live Usama conversation. It alerts "
        "when an earlier appointment date appears, or when login/CAPTCHA/security verification "
        "is required. It never bypasses verification and never auto-books."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "start | stop | check | status"},
            "current_appointment": {
                "type": "STRING",
                "description": "User's currently booked appointment date, preferably YYYY-MM-DD."
            },
            "url": {
                "type": "STRING",
                "description": "Optional visa appointment URL. Usually omit it and attach to the open logged-in visa tab."
            }
        },
        "required": ["action"]
    },
    "handler": visa_monitor,
}


if __name__ == "__main__" and "--check" in sys.argv:
    result = check_once(notify=True)
    try:
        print(json.dumps(result, ensure_ascii=False))
    except Exception:
        pass
