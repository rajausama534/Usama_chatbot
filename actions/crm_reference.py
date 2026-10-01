"""
Static operational reference for Usama CRM.

This is intentionally a schema/navigation guide, not a cache of live CRM data.
Live counts, records and statuses must always be read from the logged-in CRM.
"""

CRM_REFERENCE = {
    "modules": [
        "Dashboard",
        "Leads",
        "Follow-up Reminders",
        "Owner Database",
        "Owner Finder",
        "Cluster Guide",
        "Calendar",
        "WhatsApp Broadcast",
        "Unit Finder",
    ],
    "lead_fields": [
        "lead_receive_date", "name", "phone", "email", "project_inquired",
        "budget", "property_type", "bedroom", "source", "status",
        "follow_up_date", "follow_up_time", "reminder_type", "reminder_note",
        "notes", "last_contacted",
    ],
    "lead_statuses": [
        "New", "Contacted", "Call Back", "Interested",
        "Viewing", "Negotiation", "Lost",
    ],
    "owner_fields": [
        "community", "cluster", "unit", "owner", "phone1", "phone2",
        "status", "remarks", "admin_remarks", "agent_remarks",
        "data_source", "last_contacted",
    ],
    "owner_finder_search": "name, phone, project/community, cluster/building, or unit",
    "followup": {
        "dashboard": "shows overdue, today and upcoming callbacks",
        "reminder_types": ["Call", "WhatsApp", "Meeting", "General Follow-up"],
    },
    "message_rules": [
        "resolve the exact lead/owner record first",
        "verify the displayed name plus phone/property context before messaging",
        "prepare the WhatsApp message using the resolved contact",
        "sending uses the normal single final confirmation gate",
        "after contact, verify CRM last_contacted/status/activity if the CRM updates it",
    ],
}


def crm_reference(parameters=None, **kwargs):
    p = parameters or {}
    section = str(p.get("section", "all")).strip().lower()

    if section in ("modules", "navigation"):
        return "CRM modules: " + ", ".join(CRM_REFERENCE["modules"])
    if section in ("lead", "leads"):
        return (
            "Lead statuses: " + " -> ".join(CRM_REFERENCE["lead_statuses"]) +
            "\nLead fields: " + ", ".join(CRM_REFERENCE["lead_fields"])
        )
    if section in ("owner", "owners", "owner database"):
        return (
            "Owner fields: " + ", ".join(CRM_REFERENCE["owner_fields"]) +
            "\nOwner Finder searches by " + CRM_REFERENCE["owner_finder_search"] + "."
        )
    if section in ("followup", "follow-up", "follow ups", "follow-ups"):
        f = CRM_REFERENCE["followup"]
        return (
            "Follow-up Reminders " + f["dashboard"] + ". Reminder types: " +
            ", ".join(f["reminder_types"]) + "."
        )
    if section in ("message", "messaging", "whatsapp"):
        return "Messaging workflow: " + "; ".join(CRM_REFERENCE["message_rules"]) + "."
    return (
        "CRM modules: " + ", ".join(CRM_REFERENCE["modules"]) +
        "\nLead statuses: " + " -> ".join(CRM_REFERENCE["lead_statuses"]) +
        "\nLead fields: " + ", ".join(CRM_REFERENCE["lead_fields"]) +
        "\nOwner fields: " + ", ".join(CRM_REFERENCE["owner_fields"]) +
        "\nOwner Finder searches by " + CRM_REFERENCE["owner_finder_search"] + "."
    )


TOOL = {
    "name": "crm_reference",
    "description": (
        "Authoritative structural guide for the user's Usama CRM. Use it before CRM work "
        "when you need the real module names, lead pipeline fields/statuses, owner fields, "
        "follow-up structure, or messaging workflow. It contains no live CRM values."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "section": {
                "type": "STRING",
                "description": "all | modules | leads | owners | followup | messaging"
            }
        },
        "required": []
    },
    "handler": crm_reference,
}
