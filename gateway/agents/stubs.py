"""Agents 4 & 5 stubs — execution and report.

Real simulator execution (esmini→MCAP→MinIO→Foxglove) and the report
service do not exist yet (plan Phase 5). These return the same coherent
AEB fixtures the frontend uses today (pipelineStore.buildAebExecution /
REPORT_RESULT) so the orchestration chain works end-to-end now.
"""

from datetime import datetime, timezone
from typing import Any


def execute_simulation(test_cases: list[dict[str, Any]]) -> dict[str, Any]:
    cases = [
        {"id": tc.get("scenario_id", f"TC-{i + 1:03d}"), "feature": tc.get("feature_under_test", "AEB")}
        for i, tc in enumerate(test_cases)
    ] or [
        {"id": "TC-AEB-01", "feature": "AEB Pedestrian — nominal"},
        {"id": "TC-AEB-02", "feature": "AEB Pedestrian — lower speed"},
        {"id": "TC-AEB-03", "feature": "AEB Pedestrian — occluded"},
    ]
    n = len(cases)

    def stamp(sec: int) -> str:
        return datetime(2026, 1, 1, 9, 14, 1 + sec, tzinfo=timezone.utc).strftime("%H:%M:%S")

    logs: list[dict[str, Any]] = [
        {"id": "exec-spawn", "type": "info",
         "text": f"Spawning simulation workers · {n} scenario{'s' if n > 1 else ''} queued",
         "timestamp": stamp(0)},
    ]
    for i, case in enumerate(cases):
        detail = " · TTC min 1.14 s · stop 2.7 m clearance" if i == 0 else f" · TTC min {1.2 + i * 0.3:.2f} s"
        logs.append({
            "id": f"exec-run-{i}", "type": "ok",
            "text": f"RUN-{i + 1:03d} — {case['id']} ({case['feature']}) · passed{detail}",
            "timestamp": stamp(6 * (i + 1)),
        })
    logs.append({"id": "exec-done", "type": "info",
                 "text": f"All {n} scenarios complete. Generating report…",
                 "timestamp": stamp(6 * (n + 1))})

    return {"total": n, "passed": n, "failed": 0, "requeued": 0, "logs": logs, "stub": True}


def evaluate_results(execution: dict[str, Any]) -> dict[str, Any]:
    return {
        "verdict": "pass",
        "score": 96,
        "kpis": [
            {"name": "Min TTC",           "value": "1.14", "unit": "s",     "status": "pass"},
            {"name": "Min clearance",     "value": "2.7",  "unit": "m",     "status": "pass"},
            {"name": "AEB reaction time", "value": "285",  "unit": "ms",    "status": "pass"},
            {"name": "Detection rate",    "value": "99.8", "unit": "%",     "status": "pass"},
            {"name": "False positives",   "value": "0",    "unit": "count", "status": "pass"},
            {"name": "Approach speed",    "value": "50",   "unit": "km/h",  "status": "pass"},
        ],
        "scenarios_evaluated": execution.get("total", 0),
        "stub": True,
    }
