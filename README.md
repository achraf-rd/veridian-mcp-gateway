# Veridian MCP Gateway

MCP server (Streamable HTTP) that exposes the Veridian ADAS validation pipeline to the LLM orchestrator:

| Primitive | What |
|---|---|
| **Tools** | `refine_requirements` (Agent 1), `generate_test_cases` (Agent 2), `generate_xosc` (Agent 3), `execute_simulation` (Agent 4 — stub), `evaluate_results` (Agent 5 — stub) |
| **Resources** | `project://{id}/conversations` (index), `conversation://{id}/summary` (~300-token projection), `conversation://{id}/testcases/{tcId}` (drill-down) |
| **Prompts** | `full_pipeline`, `direct_testcase`, `replay_with_mods`, `reevaluate` — the 4 smart-routing flows, surfaced in the app as composer slash commands |

Design (Option A, split planes): **MCP is the control plane** — tool calls start agents and return `job_id` + the final result the orchestrator reasons over, with coarse `notifications/progress` ticks. **The app's existing SSE routes stay the telemetry plane** for the rich per-scenario cards. See `../Veridian_frontend/.claude/orchestrator-mcp-plan.md`.

## Run

```bash
cp .env.example .env        # defaults already point at the Fly.dev agents
uv sync                     # pulls managed Python 3.12 + deps
uv run python server.py     # Streamable HTTP on http://127.0.0.1:8100/mcp
```

`DATABASE_URL` (same Postgres as the Next.js app) is only needed for the resources; tools and prompts work without it.

## Test

```bash
uv run python tests/smoke_test.py     # in-memory, no port, no agent network calls
```

Interactive poking, once running:

```bash
npx @modelcontextprotocol/inspector   # transport: Streamable HTTP → http://127.0.0.1:8100/mcp
```

Real end-to-end tool call (hits the live Agent 1 on Fly.dev):

```bash
npx @modelcontextprotocol/inspector --cli http://127.0.0.1:8100/mcp \
  --transport http --method tools/call --tool-name refine_requirements \
  --tool-arg 'requirements=["The AEB system shall stop the vehicle before hitting a pedestrian crossing at 50 km/h."]'
```

## Notes

- Agents 2/3 stream for minutes upstream; the tools consume the SSE internally and return only the final payload. No client-side timeout is set on reads.
- A per-scenario `stage: error` event from Agent 3 is an internal retry, **not** a failure; only a top-level `error` with no summary aborts the tool.
- Agents 4/5 are stubs returning the frontend's coherent AEB fixtures (`"stub": true`) until the esmini execution chain ships (plan Phase 5).
- RBAC: resources currently trust the caller (internal service). Before any non-local deployment, forward the caller identity (role + clientDomain) and scope the SQL exactly like `GET /api/projects` does.
