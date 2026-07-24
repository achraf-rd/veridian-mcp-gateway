"""Agent 2 — Test Case Generator (agenticve-testing.fly.dev)."""

from typing import Any

import httpx

from gateway.config import AGENT2_URL
from gateway.agents.sse import stream_json_events
from gateway.agents.agent1 import ProgressFn
from gateway import job_registry


async def generate_test_cases(
    refining_id: str | None,
    feature: str | None,
    requirements: list[dict[str, Any]],
    on_progress: ProgressFn,
) -> dict[str, Any]:
    """Run the test-case generation stream to completion.

    Upstream events are keyed on `status`: started (carries job_id),
    running (progress message), done (final payload with scenarios[]).
    Returns { job_id, refining_id, feature, total_scenarios, scenarios }.
    """
    payload = {"refining_id": refining_id, "feature": feature, "requirements": requirements}
    job_id: str | None = None
    ticks = 0

    async for event in stream_json_events(f"{AGENT2_URL}/generate/stream", payload):
        status = event.get("status")
        if status == "started":
            job_id = event.get("job_id") or job_id
            job_registry.set_job("generate_test_cases", job_id)  # so a Stop can halt it
            await on_progress(0, None, event.get("message", "started"))
        elif status == "running":
            ticks += 1
            await on_progress(ticks, None, event.get("message", "running"))
        elif status == "done":
            job_registry.clear_job("generate_test_cases")
            return {
                "job_id": job_id,
                "refining_id": event.get("refining_id"),
                "feature": event.get("feature"),
                "total_scenarios": event.get("total_scenarios", 0),
                "scenarios": event.get("scenarios", []),
            }
        elif status == "error":
            raise RuntimeError(f"Agent 2 error: {event.get('message') or 'unknown'}")
    raise RuntimeError("Agent 2 stream ended without a done event")


async def stop(job_id: str) -> dict[str, Any]:
    """Cancel a running generation stream by job_id."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(f"{AGENT2_URL}/generate/stop", json={"job_id": job_id})
        response.raise_for_status()
        return response.json()
