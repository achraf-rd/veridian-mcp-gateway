"""Veridian MCP Gateway — Streamable HTTP MCP server.

Exposes the 5 pipeline agents as tools, Postgres-backed conversation/
project context as resources, and the 4 smart-routing flows as prompts.
Consumed by the Veridian orchestrator (LangGraph) as its control plane;
live telemetry stays on the app's own SSE routes.
"""

from fastmcp import FastMCP

from gateway import perf, prompts, resources, tools
from gateway.config import GATEWAY_HOST, GATEWAY_PORT

perf.setup_logging()  # timing logs → the gateway terminal

mcp = FastMCP(
    name="veridian-agents",
    instructions=(
        "Gateway to the Veridian ADAS validation pipeline. For a new batch of raw "
        "requirements the order is fixed: refine_requirements -> generate_test_cases "
        "-> generate_xosc -> execute_simulation -> evaluate_results, with human "
        "approval gates between the first three handled by the caller. Read "
        "conversation://{id}/summary before acting on an existing conversation; "
        "IDs are not guessable — discover them via project://{id}/conversations."
    ),
)

tools.register(mcp)
resources.register(mcp)
prompts.register(mcp)

if __name__ == "__main__":
    mcp.run(transport="http", host=GATEWAY_HOST, port=GATEWAY_PORT)
