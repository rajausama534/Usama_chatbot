"""Read-only client for the existing Usama CRM Supabase project.

Authentication is interactive on the owner's Mac; only a refresh token is kept
in the OS keychain, never in GitHub, plaintext config or Gemini prompts.
Uses the same public project URL / publishable key as the existing CRM frontend.
"""
from __future__ import annotations
import getpass
import os
import re
from datetime import date, timedelta
from urllib.parse import urlparse

import requests

CRM_URL = "https://vnydxkmhrcesdffpfjpc.supabase.co"
PUBLISHABLE_KEY = "sb_publishable_VP8ZvA5up64JFGkn5_7qbg_NYVJvt-I"
SERVICE = "usama-crm-supabase-refresh"
USER = "crm-owner"
_ACCESS = None
_REFRESH = None

def _keychain():
    try:
        import keyring
        return keyring
    except ImportError as exc:
        raise RuntimeError("Install secure OS keychain support: pip install keyring") from exc

def _headers(jwt=None):
    headers = {"apikey": PUBLISHABLE_KEY, "Accept": "application/json"}
    headers["Authorization"] = "Bearer " + (jwt or PUBLISHABLE_KEY)
    return headers

def _check_host():
    if urlparse(CRM_URL).hostname != "vnydxkmhrcesdffpfjpc.supabase.co":
        raise RuntimeError("CRM project URL does not match the verified existing CRM")

def login():
    """Run only in an owner's local terminal, never from the model."""
    _check_host()
    email = input("Existing CRM login email: ").strip()
    password = getpass.getpass("Existing CRM password (not stored): ")
    try:
        response = requests.post(
            CRM_URL + "/auth/v1/token",
            params={"grant_type": "password"},
            json={"email": email, "password": password},
            headers=_headers(), timeout=18,
        )
        response.raise_for_status()
        data = response.json()
        refresh = data.get("refresh_token")
        if not refresh or not data.get("access_token"):
            raise RuntimeError("CRM did not return a valid authenticated session")
        _keychain().set_password(SERVICE, USER, refresh)
        return "CRM authenticated. Refresh token securely saved to the OS keychain."
    except requests.RequestException as exc:
        return f"CRM login failed ({type(exc).__name__}); verify your existing CRM login."
    finally:
        password = None

def logout():
    global _ACCESS, _REFRESH
    _ACCESS = _REFRESH = None
    k = _keychain()
    try:
        k.delete_password(SERVICE, USER)
    except Exception:
        pass
    return "Local CRM authorization removed."

def _jwt():
    global _ACCESS, _REFRESH
    _check_host()
    if _ACCESS:
        return _ACCESS
    saved = _keychain().get_password(SERVICE, USER)
    if not saved:
        raise RuntimeError("CRM is not authorized. Run: python3 -m core.crm_client login")
    response = requests.post(
        CRM_URL + "/auth/v1/token",
        params={"grant_type": "refresh_token"},
        json={"refresh_token": saved},
        headers=_headers(), timeout=18,
    )
    if response.status_code in (400, 401, 403):
        raise RuntimeError("CRM authorization expired. Run local CRM login again.")
    response.raise_for_status()
    data = response.json()
    _ACCESS = data["access_token"]
    rotated = data.get("refresh_token")
    if rotated and rotated != saved:
        _keychain().set_password(SERVICE, USER, rotated)
    return _ACCESS

def _get(table, query):
    if table not in {"leads", "owners"}:
        raise ValueError("Only existing CRM leads and owners may be read")
    try:
        response = requests.get(
            CRM_URL + "/rest/v1/" + table,
            headers=_headers(_jwt()),
            params=query, timeout=18,
        )
        if response.status_code == 401:
            # Access tokens expire. Try rotating the refresh token once; never
            # retry writes (this client exposes GET only).
            global _ACCESS
            _ACCESS = None
            response = requests.get(
                CRM_URL + "/rest/v1/" + table,
                headers=_headers(_jwt()), params=query, timeout=18,
            )
        if response.status_code in (401, 403):
            return {"error": "CRM session or row-level permissions do not allow this read."}
        response.raise_for_status()
        rows = response.json()
        if not isinstance(rows, list):
            return {"error": "Unexpected CRM response."}
        return {"records": rows, "count": len(rows)}
    except requests.RequestException as exc:
        return {"error": f"CRM read failed ({type(exc).__name__}). No data was changed."}

def _term(text):
    cleaned = re.sub(r"[^\w \-]", " ", str(text or ""), flags=re.UNICODE)
    cleaned = " ".join(cleaned.split())[:75]
    if len(cleaned) < 2:
        raise ValueError("Please provide at least two letters to search.")
    return cleaned

def find_leads(query, limit=10):
    return _get("leads", {
        "select": "id,name,phone,status,project_inquired,follow_up_date,follow_up_time,reminder_type,reminder_note,last_contacted",
        "name": "ilike.*" + _term(query).replace(" ", "*") + "*",
        "limit": str(min(20, max(1, int(limit)))),
    })

def find_owners(query, limit=10):
    return _get("owners", {
        "select": "id,owner,community,cluster,unit",
        "owner": "ilike.*" + _term(query).replace(" ", "*") + "*",
        "limit": str(min(20, max(1, int(limit)))),
    })

def followups(days=7, limit=20):
    days = min(30, max(0, int(days)))
    return _get("leads", {
        "select": "id,name,phone,status,project_inquired,follow_up_date,follow_up_time,reminder_type,reminder_note",
        "follow_up_date": "gte." + date.today().isoformat(),
        "and": "(follow_up_date.lte." + (date.today() + timedelta(days=days)).isoformat() + ")",
        "order": "follow_up_date.asc",
        "limit": str(min(50, max(1, int(limit)))),
    })

if __name__ == "__main__":
    import sys
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "login":
        print(login())
    elif command == "logout":
        print(logout())
    else:
        print("Use: python3 -m core.crm_client login | logout")
