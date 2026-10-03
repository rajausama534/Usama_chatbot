"""Offline checks: inspect only a unique lead and never write records."""
import json
import unittest
from unittest.mock import patch
from actions.crm_inspect import crm_inspect


class CRMInspectTests(unittest.TestCase):
    @patch("actions.crm_inspect.crm_client._get")
    @patch("actions.crm_inspect.crm_client.find_leads")
    def test_unique_match_reads_full_record(self, find, get):
        find.return_value = {"records": [{"id": "abc-123", "name": "Raja"}]}
        get.return_value = {"records": [{"id": "abc-123", "name": "Raja", "notes": "Call tomorrow"}]}
        reply = json.loads(crm_inspect({"query": "Raja"}))
        self.assertTrue(reply["read_only"])
        self.assertEqual(reply["lead"]["notes"], "Call tomorrow")
        get.assert_called_once_with("leads", {"select": "*", "id": "eq.abc-123", "limit": "1"})

    @patch("actions.crm_inspect.crm_client._get")
    @patch("actions.crm_inspect.crm_client.find_leads")
    def test_ambiguous_match_does_not_open_arbitrary_record(self, find, get):
        find.return_value = {"records": [{"id": "1", "name": "Ali"}, {"id": "2", "name": "Ali"}]}
        result = json.loads(crm_inspect({"query": "Ali"}))
        self.assertEqual(len(result["matches"]), 2)
        get.assert_not_called()

    @patch("actions.crm_inspect.crm_client._get")
    def test_large_record_does_not_return_broken_json(self, get):
        get.return_value = {"records": [{"id": "abc-123", "notes": "x" * 20000}]}
        reply = json.loads(crm_inspect({"lead_id": "abc-123"}))
        self.assertTrue(reply["read_only"])
        self.assertEqual(reply["lead_id"], "abc-123")
        self.assertNotIn("lead", reply)

    @patch("actions.crm_inspect.crm_client._get")
    def test_invalid_id_never_queries_database(self, get):
        self.assertIn("Invalid lead identifier", crm_inspect({"lead_id": "abc;delete"}))
        get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
