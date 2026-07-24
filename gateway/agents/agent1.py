"""Agent 1 — Requirements Refiner (adas-req-refiner.fly.dev)."""

from typing import Any, Callable, Awaitable

import httpx

from gateway.config import AGENT1_URL
from gateway.agents.sse import stream_json_events
from gateway import job_registry

ProgressFn = Callable[[float, float | None, str], Awaitable[None]]


async def refine(requirements: list[str], on_progress: ProgressFn) -> dict[str, Any]:
    """Run the refinement stream to completion; return the RefinementResult.

    Upstream events: {type: pipeline_id|stage|attempt|validation_failed|result|error}.
    The first frame carries `pipeline_id` (registered so a Stop can cancel it);
    only `result` carries the payload (in `output`); `error` is fatal.
    """
    stages_seen = 0
    async for event in stream_json_events(f"{AGENT1_URL}/refine/stream", {"requirements": requirements}):
        etype = event.get("type")
        if etype == "pipeline_id":
            job_registry.set_job("refine_requirements", event.get("id"))  # so a Stop can halt it
        elif etype == "stage":
            stages_seen += 1
            await on_progress(stages_seen, None, f"{event.get('name', 'stage')}: {event.get('status', '')}")
        elif etype == "result":
            job_registry.clear_job("refine_requirements")
            return event.get("output", {})
        elif etype == "error":
            job_registry.clear_job("refine_requirements")
            raise RuntimeError(f"Agent 1 error: {event.get('detail') or event.get('message') or 'unknown'}")
    job_registry.clear_job("refine_requirements")
    raise RuntimeError("Agent 1 stream ended without a result event")


async def stop(pipeline_id: str) -> dict[str, Any]:
    """Cancel a running refinement by pipeline_id (POST /refine/cancel/{id})."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(f"{AGENT1_URL}/refine/cancel/{pipeline_id}")
        response.raise_for_status()
        return response.json()
