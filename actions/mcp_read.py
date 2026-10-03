"""Optional read-only MCP bridge for Usama's discoverable action system.

Configure MCP servers in config/mcp_servers.json (local file, NOT committed).
Server commands are read only from that file, never from a model response.
Only tools explicitly configured in USAMA_MCP_READ_ALLOWLIST can be called.
Sending messages, trading, and other writes are deliberately disabled here.
"""
import asyncio
import json
import os
import threading
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_CONFIG = _ROOT / "config" / "mcp_servers.json"

def _servers():
    if not _CONFIG.is_file():
        return {}
    raw = json.loads(_CONFIG.read_text(encoding="utf-8"))
    servers = raw.get("mcpServers", {})
    if not isinstance(servers, dict):
        raise ValueError("mcpServers must be an object")
    return servers

def _read_allowlist():
    # Format: server:tool,server:tool. No wildcard: every operation is reviewed.
    return {x.strip() for x in os.environ.get("USAMA_MCP_READ_ALLOWLIST", "").split(",") if x.strip()}

async def _invoke(server, tool, arguments):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    cfg = _servers()[server]
    if not isinstance(cfg, dict) or not cfg.get("command"):
        raise ValueError("MCP server must have a configured command")
    env = {**os.environ, **{str(k): str(v) for k, v in cfg.get("env", {}).items()}}
    params = StdioServerParameters(command=cfg["command"], args=cfg.get("args", []), env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            available = await session.list_tools()
            if tool not in {item.name for item in available.tools}:
                raise ValueError("Tool is not advertised by the configured MCP server")
            selected = next(t for t in available.tools if t.name == tool)
            annotations = getattr(selected, "annotations", None)
            if annotations is not None and getattr(annotations, "readOnlyHint", None) is False:
                return "Refused: MCP server marks this tool as not read-only."
            # The user must review and allowlist genuinely read-only tools;
            # deny common mutation verbs even when an untrusted server mislabels one.
            prohibited = ("send", "delete", "remove", "update", "write", "create",
                          "post", "publish", "trade", "execute", "insert", "upsert",
                          "refund", "fulfill", "cancel", "book", "schedule", "transfer")
            words = set(__import__("re").split(r"[^a-z0-9]+", tool.lower()))
            if words.intersection(prohibited):
                return "Refused: this operation may change external data."
            result = await session.call_tool(tool, arguments)
            if result.isError:
                return "MCP tool reported an error."
            return "\n".join(str(getattr(item, "text", "")) for item in result.content)[:12000]

def _run_coro_in_thread(coro):
    output = {}
    def runner():
        try:
            output["result"] = asyncio.run(asyncio.wait_for(coro, timeout=30))
        except Exception as exc:
            output["error"] = exc
    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join(timeout=32)
    if thread.is_alive():
        return "MCP read timed out. No write operation was attempted."
    if "error" in output:
        raise output["error"]
    return output.get("result", "")

def mcp_read(parameters):
    server = str(parameters.get("server", "")).strip()
    tool = str(parameters.get("tool", "")).strip()
    if not server or not tool:
        return "Specify an MCP server and a read-only tool."
    if f"{server}:{tool}" not in _read_allowlist():
        return "MCP operation not authorized. Configure a reviewed read-only tool in USAMA_MCP_READ_ALLOWLIST."
    try:
        raw = parameters.get("arguments_json", "")
        args = json.loads(raw) if raw else parameters.get("arguments", {})
        if not isinstance(args, dict):
            return "MCP arguments must be a JSON object."
        if server not in _servers():
            return "MCP server not configured locally."
        return _run_coro_in_thread(_invoke(server, tool, args))
    except ImportError:
        return "MCP support not installed. Run: pip install mcp"
    except Exception as exc:
        # Do not leak server args, tokens, environment variables, or tool payloads.
        return f"MCP read failed ({type(exc).__name__}). Check local MCP settings and logs."

TOOL = {
    "name": "mcp_read",
    "description": "Call a locally configured, explicitly allowlisted read-only MCP tool (e.g. search Gmail). Never use for sending messages, writing records or placing trades. The server and tool must already be configured by the user.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "server": {"type": "STRING"},
            "tool": {"type": "STRING"},
            "arguments_json": {"type": "STRING", "description": "Optional JSON object containing the exact arguments of the discovered read-only tool"},
            "arguments": {"type": "OBJECT", "properties": {}}
        },
        "required": ["server", "tool"]
    },
    "handler": mcp_read,
}
