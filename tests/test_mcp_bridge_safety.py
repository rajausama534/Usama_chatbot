"""Offline checks. These tests never connect to external MCP servers."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from actions import mcp_read, mcp_discover


class MCPBridgeSafetyTests(unittest.TestCase):
    def test_no_read_allowlist_means_no_call(self):
        with patch.dict("os.environ", {"USAMA_MCP_READ_ALLOWLIST": ""}), \
             patch.object(mcp_read, "_run_coro_in_thread") as run:
            message = mcp_read.mcp_read({
                "server": "gmail", "tool": "list_messages",
                "arguments_json": json.dumps({"max_results": 1})})
            self.assertIn("not authorized", message)
            run.assert_not_called()

    def test_server_not_configured(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(mcp_read, "_CONFIG", Path(tmp) / "missing.json"), \
             patch.dict("os.environ", {"USAMA_MCP_READ_ALLOWLIST": "gmail:list_messages"}):
            message = mcp_read.mcp_read({"server": "gmail", "tool": "list_messages"})
            self.assertIn("not configured", message)

    def test_invalid_tool_arguments_rejected_without_call(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(mcp_read, "_CONFIG", Path(tmp) / "config.json"), \
             patch.dict("os.environ", {"USAMA_MCP_READ_ALLOWLIST": "gmail:list_messages"}), \
             patch.object(mcp_read, "_run_coro_in_thread") as run:
            (Path(tmp) / "config.json").write_text(
                json.dumps({"mcpServers": {"gmail": {"command": "example"}}}),
                encoding="utf-8")
            result = mcp_read.mcp_read({
                "server": "gmail", "tool": "list_messages",
                "arguments_json": '["not an object"]'})
            self.assertIn("JSON object", result)
            run.assert_not_called()

    def test_discovery_unconfigured_does_not_spawn_server(self):
        with patch.object(mcp_discover, "_servers", return_value={}), \
             patch.object(mcp_discover, "_run_coro_in_thread") as run:
            result = mcp_discover.mcp_discover({"server": "shopify"})
            self.assertIn("not configured", result)
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
