"""Latest live job_id per long-running agent, so a Stop can halt it mid-run.

Only Agents 2 (generate_test_cases) and 3 (generate_xosc) expose an upstream
/generate/stop; Agent 1 (refiner) and Agent 4 (executor) have none. Keyed by
agent name (latest job wins) — fine for the one-run-at-a-time orchestrator.
"""

_ACTIVE: dict[str, str] = {}


def set_job(agent: str, job_id: str | None) -> None:
    if job_id:
        _ACTIVE[agent] = job_id


def get_job(agent: str) -> str | None:
    return _ACTIVE.get(agent)


def clear_job(agent: str) -> None:
    _ACTIVE.pop(agent, None)
