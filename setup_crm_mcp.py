"""Install the existing CRM MCP entry without touching production CRM data.

Run from the Usama project root with the project's active Python interpreter.
Existing MCP entries and local credentials are preserved.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "config" / "mcp_servers.json"


def main():
    if TARGET.exists():
        data = json.loads(TARGET.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("mcpServers", {}), dict):
            raise ValueError("Existing MCP configuration is invalid; no changes made.")
    else:
        data = {"mcpServers": {}}
    servers = data.setdefault("mcpServers", {})
    if "existing_crm" in servers:
        print("Existing CRM MCP entry already exists; left unchanged.")
        return
    servers["existing_crm"] = {
        "command": sys.executable,
        "args": ["-m", "core.crm_mcp_server"],
    }
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    temp = TARGET.with_suffix(".json.tmp")
    try:
        with temp.open("w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        if os.name != "nt":
            os.chmod(temp, 0o600)
        os.replace(temp, TARGET)
    finally:
        if temp.exists():
            temp.unlink()
    print("Existing CRM MCP configured locally. Other entries preserved.")
    print("Authentication and real Mac testing are separate steps.")


if __name__ == "__main__":
    main()
