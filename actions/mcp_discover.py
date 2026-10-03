"""Inspect real tools of a locally configured stdio MCP server, without calling them.

The AI must never invent a tool name or attempt writes during discovery.
"""
import asyncio
from actions.mcp_read import _servers, _run_coro_in_thread


async def _discover(server):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from os import environ
    cfg = _servers()[server]
    if not isinstance(cfg, dict) or not cfg.get("command"):
        raise ValueError("Missing configured command")
    env = {**environ, **{str(k): str(v) for k, v in cfg.get("env", {}).items()}}
    params = StdioServerParameters(command=cfg["command"], args=cfg.get("args", []), env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            return [{"name": t.name,
                     "description": (t.description or "")[:180],
                     "read_only": bool(getattr(getattr(t, "annotations", None), "readOnlyHint", False))}
                    for t in tools.tools][:80]


def mcp_discover(parameters):
    server = str((parameters or {}).get("server", "")).strip()
    if not server:
        return "Specify the configured MCP server name."
    try:
        if server not in _servers():
            return "Server is not configured locally. No connection attempted."
        items = _run_coro_in_thread(_discover(server))
        if isinstance(items, str):
            return items
        if not items:
            return "Server connected but advertised no tools."
        import json
        return json.dumps({"server": server, "tools": items}, ensure_ascii=False)
    except ImportError:
        return "MCP SDK missing. Install in your Mac virtual environment: pip install mcp"
    except Exception as exc:
        return (f"MCP discovery failed ({type(exc).__name__}). Check server configuration "
                "and local account authentication; no tools were invoked.")


TOOL = {
    "name": "mcp_discover",
    "description": "List actual tools advertised by a locally configured MCP server without invoking them. Use this before any MCP read; configuration alone does not prove authentication. Never assume a tool is read-only from its name alone.",
    "parameters": {"type": "OBJECT", "properties": {
        "server": {"type": "STRING", "description": "Exact configured server name"}
    }, "required": ["server"]},
    "handler": mcp_discover,
}
