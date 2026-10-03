"""Open the real existing Usama CRM website (Vercel), not the Supabase API.

Opening the URL is a best-effort browser action. The CRM still requires its
normal login; opening a tab does not confirm that the page loaded.
"""
import webbrowser
from core.crm_client import CRM_WEBSITE_URL


def open_crm(parameters):
    try:
        launched = webbrowser.open(CRM_WEBSITE_URL, new=2)
    except Exception as exc:
        return f"Could not open your CRM website ({type(exc).__name__})."
    if not launched:
        return ("Browser did not confirm opening the CRM. "
                f"Open this address manually: {CRM_WEBSITE_URL}")
    return (f"Requested your browser to open the existing CRM: {CRM_WEBSITE_URL}. "
            "Page loading and sign-in have not been verified.")


TOOL = {
    "name": "open_crm",
    "description": "Open the user's EXISTING CRM website at https://usama-crm.vercel.app/ in their browser. Never open the Supabase data API as the CRM website. This action does not read or edit records.",
    "parameters": {"type": "OBJECT", "properties": {}},
    "handler": open_crm,
}
