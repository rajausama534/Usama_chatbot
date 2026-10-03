"""Offline regression tests: no credentials, live accounts or CRM writes."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from actions import integration_status as mod


class TestIntegrationStatus(unittest.TestCase):
    def test_all_seven_services_are_reported_without_configuration(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(mod, "ROOT", Path(folder)):
            result = json.loads(mod.integration_status({}))
        self.assertEqual(set(result), set(mod.SERVICES))
        self.assertEqual(result["shopify"], "not configured")
        self.assertEqual(result["supabase"], "not configured")

    def test_config_does_not_claim_live_connection(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / "config"
            config.mkdir()
            (config / "mcp_servers.json").write_text(
                json.dumps({"mcpServers": {"supabase": {"command": "example-server"},
                                            "shopify": {"command": "example-server"}}}),
                encoding="utf-8")
            with patch.object(mod, "ROOT", Path(folder)):
                result = json.loads(mod.integration_status({}))
        self.assertIn("unverified", result["supabase"])
        self.assertIn("unverified", result["shopify"])

    def test_invalid_local_config_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / "config"
            config.mkdir()
            (config / "mcp_servers.json").write_text("{invalid", encoding="utf-8")
            with patch.object(mod, "ROOT", Path(folder)):
                result = json.loads(mod.integration_status({}))
        self.assertEqual(result["supabase"], "not configured")


if __name__ == "__main__":
    unittest.main()
