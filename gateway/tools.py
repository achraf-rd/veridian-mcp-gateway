"""The 5 pipeline agents exposed as MCP tools (control plane).

Long-running agents (2, 3) return { job_id, ...final result } — live
per-scenario telemetry stays on the app's SSE plane; this channel carries
the coarse result the orchestrator reasons over, plus MCP progress ticks.
"""

import json
from typing import Any

from fastmcp import Context, FastMCP

from gateway.agents import agent1, agent2, agent3, agent4, stubs
from gateway import job_registry, perf


def _progress(ctx: Context):
    async def report(progress: float, total: float | None, message: str) -> None:
        try:
            await ctx.report_progress(progress=progress, total=total, message=message)
        except Exception:
            pass  # progress is best-effort; never fail the tool for it

    return report


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": True})
    async def refine_requirements(requirements: list[str], ctx: Context) -> str:
        """Refine raw natural-language ADAS requirements (Agent 1). Classifies each as
        testable/incomplete/duplicate, flags conflicts and overlaps, assigns complexity
        and num_scenarios. Returns the full RefinementResult JSON. Call this FIRST for
        any new batch of requirements; its `testable` array feeds generate_test_cases."""
        async with perf.timed("tool:refine_requirements", n=len(requirements)):
            result = await agent1.refine(requirements, _progress(ctx))
        return json.dumps(result)

    @mcp.tool(annotations={"openWorldHint": True})
    async def generate_test_cases(
        requirements: list[dict[str, Any]],
        ctx: Context,
        refining_id: str | None = None,
        feature: str | None = None,
    ) -> str:
        """Generate structured test cases from refined requirements (Agent 2). Each
        requirement dict must have exactly {id, original, complexity, conflict_flag,
        num_scenarios, overlap_with, status:'valid'} — pass only status=='valid' items
        from refine_requirements. Long-running (streams for minutes); returns
        { job_id, total_scenarios, scenarios[] } with full SIL/HIL sections.
        Do NOT call for raw unrefined text — refine first."""
        async with perf.timed("tool:generate_test_cases", reqs=len(requirements)):
            result = await agent2.generate_test_cases(refining_id, feature, requirements, _progress(ctx))
        return json.dumps(result)

    @mcp.tool(annotations={"openWorldHint": True})
    async def generate_xosc(specs: list[dict[str, Any]], ctx: Context) -> str:
        """Generate OpenSCENARIO .xosc files from test-case specs (Agent 3). Each spec
        is a ScenarioSpec built from an Agent 2 test case (scenario_id, description,
        environment, ego_vehicle, actors, test_steps, ...). Long-running (up to 10 min);
        returns { job_id, summary } where summary has successful/fallback/failed counts
        and per-scenario output paths. Fallback means a template was used — still usable."""
        async with perf.timed("tool:generate_xosc", specs=len(specs)):
            result = await agent3.generate_xosc(specs, _progress(ctx))
        return json.dumps(result)

    @mcp.tool(annotations={"openWorldHint": True})
    async def execute_simulation(scenarios: list[dict[str, Any]], ctx: Context) -> str:
        """Execute generated .xosc scenarios in eSMini (Agent 4 — REAL, runs on
        executor-agent.fly.dev). Each `scenarios` item is { scenario_id, xosc_path }
        where xosc_path is the Agent-3 output path. Fetches each .xosc from Agent 3,
        runs it in the executor (eSMini → report + MCAP), and returns
        { total, passed, failed, runs[] } with per-run run_name, min_distance_m,
        scenario_type, mcap_path, report_path. passed/failed = ran-to-completion vs
        errored — NOT a safety verdict (that is Agent 5's job). Long-running: reports
        progress per scenario."""
        async with perf.timed("tool:execute_simulation", scenarios=len(scenarios)):
            result = await agent4.execute(scenarios, _progress(ctx))
        return json.dumps(result)

    @mcp.tool(annotations={"openWorldHint": True})
    async def stop_agent(agent: str, ctx: Context) -> str:
        """Halt a currently-running long agent by its live job. Supported for
        refine_requirements (Agent 1), generate_test_cases (Agent 2) and
        generate_xosc (Agent 3) — each exposes an upstream cancel. Agent 4
        (executor) has none. Best-effort; safe if nothing is running."""
        job = job_registry.get_job(agent)
        if not job:
            return json.dumps({"stopped": False, "reason": "no active job"})
        try:
            if agent == "refine_requirements":
                res = await agent1.stop(job)
            elif agent == "generate_test_cases":
                res = await agent2.stop(job)
            elif agent == "generate_xosc":
                res = await agent3.stop(job)
            else:
                return json.dumps({"stopped": False, "reason": "agent not stoppable"})
            job_registry.clear_job(agent)
            return json.dumps({"stopped": True, "job_id": job, "result": res})
        except Exception as exc:  # noqa: BLE001 — Stop is best-effort
            return json.dumps({"stopped": False, "error": str(exc)})

    @mcp.tool(annotations={"readOnlyHint": True})
    async def evaluate_results(execution: dict[str, Any], ctx: Context) -> str:
        """Evaluate an ExecutionResult into a KPI report (Agent 5). Returns
        { verdict, score, kpis[] } (Min TTC, clearance, reaction time, ...).
        CURRENTLY A STUB: returns the fixed AEB report fixture — carries "stub": true."""
        return json.dumps(stubs.evaluate_results(execution))
