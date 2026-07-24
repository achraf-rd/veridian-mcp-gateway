"""Agent 4 — ADAS Scenario Executor (executor-agent.fly.dev).

Runs each Agent-3-generated .xosc in eSMini and returns the executor's raw
per-scenario metrics (min inter-vehicle distance, scenario type) plus the
MCAP/report handles. The executor works one .xosc at a time and can't reach
Agent 3's disk, so — exactly like the frontend's runByAgent3File — we fetch each
.xosc from Agent 3 by basename, make it eSMini-compatible, then upload+run it.

No pass/fail here: the executor only measures. `passed`/`failed` mean
ran-to-completion vs errored; the safety verdict is Agent 5's job.
"""

import re
from typing import Any, Awaitable, Callable
from urllib.parse import quote

import httpx

from gateway.config import AGENT3_URL, EXECUTOR_URL

ProgressFn = Callable[[float, float | None, str], Awaitable[None]]

# eSMini road bundled with the executor. Only *legacy* CARLA output (a Town## road
# eSMini can't load) is rewritten; native eSMini scenarios pass through untouched.
_ESMINI_ROAD = "../xodr/e6mini.xodr"
_PER_SCENARIO_TIMEOUT = 600.0  # eSMini run + the executor's LLM analysis


def to_esmini_compatible(xosc: str) -> str:
    if not re.search(r'<LogicFile\s+filepath="[^"]*Town\d', xosc, re.IGNORECASE):
        return xosc
    xosc = re.sub(r'<LogicFile\s+filepath="[^"]*"\s*/>', f'<LogicFile filepath="{_ESMINI_ROAD}"/>', xosc, count=1)
    xosc = re.sub(r'<SceneGraphFile\s+filepath="[^"]*"\s*/>\s*', "", xosc)
    return xosc


async def _upload_and_run(client: httpx.AsyncClient, xosc_path: str) -> dict[str, Any]:
    """Fetch one .xosc from Agent 3, normalise it, run it on the executor."""
    # Agent 3 serves files by basename at /files/{name}; a path prefix 404s.
    basename = xosc_path.split("/")[-1] or "scenario.xosc"
    got = await client.get(f"{AGENT3_URL}/files/{quote(basename)}")
    if got.status_code != 200:
        raise RuntimeError(f"agent3 file {basename}: {got.status_code}")
    xosc = to_esmini_compatible(got.text)
    # Executor keys run_name off the uploaded filename; normalise the extension
    # (Agent 3 names eSMini output *.esmini).
    upload_name = re.sub(r"\.(esmini|xosc|osc|yaml)$", "", basename, flags=re.IGNORECASE) + ".xosc"
    files = {"file": (upload_name, xosc.encode("utf-8"), "application/octet-stream")}
    resp = await client.post(f"{EXECUTOR_URL}/scenarios/upload", files=files)
    if resp.status_code != 200:
        raise RuntimeError(f"executor upload failed ({resp.status_code}): {resp.text[:200]}")
    data = resp.json()
    return {
        "run_name": data.get("run_name"),
        "scenario_type": data.get("scenario_type"),
        "min_distance_m": data.get("min_distance_m"),
        "mcap_path": data.get("mcap_path"),
        "report_path": data.get("report_path"),
        "error": data.get("error"),
    }


async def execute(scenarios: list[dict[str, Any]], on_progress: ProgressFn) -> dict[str, Any]:
    """Run each scenario's .xosc sequentially on the executor. `scenarios` items:
    { scenario_id, xosc_path }. Returns { total, passed, failed, runs[] } — raw
    metrics only, no verdict."""
    total = len(scenarios)
    runs: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=_PER_SCENARIO_TIMEOUT) as client:
        for i, sc in enumerate(scenarios):
            sid = sc.get("scenario_id") or f"scenario-{i + 1}"
            path = sc.get("xosc_path")
            await on_progress(i, total, f"executing {sid} ({i + 1}/{total})")
            if not path:
                runs.append({"scenario_id": sid, "run_name": None, "error": "no .xosc path"})
                continue
            try:
                runs.append({"scenario_id": sid, **await _upload_and_run(client, path)})
            except Exception as exc:  # noqa: BLE001 — record the failure, keep running the rest
                runs.append({"scenario_id": sid, "run_name": None, "error": str(exc)})

    passed = sum(1 for r in runs if r.get("run_name") and not r.get("error"))
    await on_progress(total, total, "execution complete")
    return {"total": total, "passed": passed, "failed": total - passed, "runs": runs}


async def health() -> bool:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{EXECUTOR_URL}/health")
            return r.status_code == 200
    except Exception:  # noqa: BLE001
        return False
