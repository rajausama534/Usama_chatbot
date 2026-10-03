"""Offline CRM tests: no external calls and no production data changes."""
import unittest
from unittest.mock import patch
from core import crm_client

class CRMReadTests(unittest.TestCase):
    def test_existing_project_pinned(self):
        self.assertEqual(crm_client.CRM_URL,
                         "https://vnydxkmhrcesdffpfjpc.supabase.co")
        crm_client._check_host()

    def test_only_existing_read_tables_allowed(self):
        with self.assertRaises(ValueError):
            crm_client._get("transactions", {})

    def test_lead_search_is_bounded(self):
        with patch.object(crm_client, "_get", return_value={"records": []}) as get:
            crm_client.find_leads("Test Name", limit=999)
        table, params = get.call_args.args
        self.assertEqual(table, "leads")
        self.assertEqual(params["limit"], "20")
        self.assertEqual(params["name"], "ilike.*Test*Name*")

    def test_owner_search_is_bounded(self):
        with patch.object(crm_client, "_get", return_value={"records": []}) as get:
            crm_client.find_owners("Test", 5)
        self.assertEqual(get.call_args.args[0], "owners")
        self.assertEqual(get.call_args.args[1]["limit"], "5")

    def test_followups_are_bounded_and_read_only(self):
        with patch.object(crm_client, "_get", return_value={"records": []}) as get:
            crm_client.followups(days=900, limit=999)
        table, params = get.call_args.args
        self.assertEqual(table, "leads")
        self.assertEqual(params["limit"], "50")
        self.assertIn("follow_up_date", params["and"])

    def test_expired_access_token_is_refreshed_only_for_read(self):
        class Reply:
            def __init__(self, code, rows=None):
                self.status_code = code
                self._rows = rows or []
            def raise_for_status(self):
                pass
            def json(self):
                return self._rows
        first, second = Reply(401), Reply(200, [{"id": "sample"}])
        with patch.object(crm_client, "_jwt", side_effect=["old", "new"]) as jwt, \
             patch.object(crm_client.requests, "get", side_effect=[first, second]) as get:
            result = crm_client._get("leads", {"select": "id", "limit": "1"})
        self.assertEqual(result["count"], 1)
        self.assertEqual(get.call_count, 2)
        self.assertEqual(jwt.call_count, 2)

    def test_short_search_not_sent(self):
        with patch.object(crm_client, "_get") as get:
            with self.assertRaises(ValueError):
                crm_client.find_leads("a")
            get.assert_not_called()

if __name__ == "__main__":
    unittest.main()
