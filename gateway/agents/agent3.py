"""Agent 3 — XOSC File Generator (adas-scenarios-gen.fly.dev)."""

from typing import Any

import httpx

from gateway.config import AGENT3_URL
from gateway.agents.sse import stream_json_events
from gateway.agents.agent1 import ProgressFn
from gateway import job_registry


async def generate_xosc(specs: list[dict[str, Any]], on_progress: ProgressFn) -> dict[str, Any]:
    """Run the XOSC generation stream to completion.

    Upstream events are keyed on `type`: started/pipeline_id (job handle),
    batch_info, scenario_start, stage, retry, scenario_done (per-scenario
    progress), summary|result (final XoscGenerationSummary), done, error.
    Per-scenario `stage: error` events mean an internal retry, NOT failure;
    only a top-level `error` with no prior summary is fatal.
    Returns { job_id, summary } — summary has successful/fallback/failed
    counts and per-scenario results with output paths.
    """
    job_id: str | None = None
    summary: dict[str, Any] | None = None
    total = len(specs)

    async for event in stream_json_events(f"{AGENT3_URL}/generate/stream", {"specs": specs}):
        etype = event.get("type")
        if etype in ("started", "pipeline_id"):
            job_id = event.get("pipeline_id") or event.get("id") or job_id
            job_registry.set_job("generate_xosc", job_id)  # so a Stop can halt it
        elif etype == "batch_info":
            total = event.get("total", total)
        elif etype == "scenario_start":
            await on_progress(
                event.get("index", 0) - 1,
                total,
                f"generating {event.get('scenario_id', '?')} ({event.get('index', '?')}/{total})",
            )
        elif etype == "scenario_done":
            await on_progress(
                event.get("index", 0),
                total,
                f"{event.get('index', '?')}/{total} {event.get('status', '')}",
            )
        elif etype in ("summary", "result"):
            summary = event.get("output") if etype == "result" else {k: v for k, v in event.items() if k != "type"}
        elif etype == "done":
            break
        elif etype == "error" and summary is None:
            raise RuntimeError(f"Agent 3 error: {event.get('detail') or event.get('message') or 'unknown'}")

    job_registry.clear_job("generate_xosc")
    if summary is None:
        raise RuntimeError("Agent 3 stream ended without a summary")
    return {"job_id": job_id, "summary": summary}


async def stop(job_id: str) -> dict[str, Any]:
    """Cancel a running XOSC pipeline by its id."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(f"{AGENT3_URL}/generate/stop", json={"job_id": job_id})
        response.raise_for_status()
        return response.json()
