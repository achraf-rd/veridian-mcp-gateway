"""MCP resources — the "Load Context from DB" node.

Read-only projections over the same Postgres the Next.js app uses
(Prisma tables "Project" / "Conversation"; pipeline state is one JSONB
column). Never returns the raw pipeline blob: summaries are ~300 tokens,
with a per-test-case drill-down template for detail on demand.
"""

import json
from typing import Any

import asyncpg
from fastmcp import FastMCP

from gateway.config import DATABASE_URL

_pool: asyncpg.Pool | None = None


async def _db() -> asyncpg.Pool:
    global _pool
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set — conversation/project resources are unavailable")
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=0, max_size=4)
    return _pool


def _pipeline(row: Any) -> dict[str, Any]:
    raw = row["pipeline"]
    if raw is None:
        return {}
    return json.loads(raw) if isinstance(raw, str) else raw


def _summarize(pipeline: dict[str, Any]) -> dict[str, Any]:
    """Project the pipeline JSONB (can be 10k+ tokens) into a small summary."""
    nlp_summary = (pipeline.get("nlpResult") or {}).get("summary") or {}
    test_cases = (pipeline.get("scenarioResult") or {}).get("testCases") or []
    xosc = pipeline.get("xoscResult") or {}
    execution = pipeline.get("executionResult") or {}
    report = pipeline.get("reportResult") or {}

    phases = [tc.get("test_phase", "SIL") for tc in test_cases]
    return {
        "round": pipeline.get("round", 1),
        "stage": pipeline.get("stage", 0),
        "status": {k: pipeline.get(k, "idle") for k in ("nlp", "scenario", "xosc", "execution", "report")},
        "requirements": {
            "testable": nlp_summary.get("total_testable", 0),
            "incomplete": nlp_summary.get("total_incomplete", 0),
            "conflicts": nlp_summary.get("total_conflicts", 0),
            "overlaps": nlp_summary.get("total_overlaps", 0),
        },
        "testCases": {
            "total": len(test_cases),
            "sil": sum(1 for p in phases if "SIL" in p),
            "hil": sum(1 for p in phases if "HIL" in p),
            "ids": [tc.get("scenario_id") for tc in test_cases],
        },
        "xosc": {k: xosc.get(k) for k in ("successful", "fallback", "failed") if k in xosc},
        "execution": {k: execution.get(k) for k in ("total", "passed", "failed", "requeued") if k in execution},
        "report": {k: report.get(k) for k in ("verdict", "score") if k in report},
    }


def register(mcp: FastMCP) -> None:
    @mcp.resource("project://{project_id}/conversations")
    async def project_conversations(project_id: str) -> str:
        """Directory of a project's conversations (batches): id, title, dates,
        pipeline stage. Use it to find a conversation id, then read
        conversation://{id}/summary for its state."""
        pool = await _db()
        rows = await pool.fetch(
            'SELECT id, title, "createdAt", "updatedAt", pipeline FROM "Conversation" '
            'WHERE "projectId" = $1 ORDER BY "updatedAt" DESC',
            project_id,
        )
        index = [
            {
                "id": row["id"],
                "title": row["title"],
                "updatedAt": row["updatedAt"].isoformat(),
                "stage": _pipeline(row).get("stage", 0),
                "round": _pipeline(row).get("round", 1),
            }
            for row in rows
        ]
        return json.dumps({"projectId": project_id, "conversations": index})

    @mcp.resource("conversation://{conversation_id}/summary")
    async def conversation_summary(conversation_id: str) -> str:
        """Token-efficient summary of one conversation's pipeline state: stage,
        per-agent status, requirement/test-case/execution/report counts. The
        "Load Context" read. For a full test case use
        conversation://{id}/testcases/{tc_id}."""
        pool = await _db()
        row = await pool.fetchrow(
            'SELECT id, title, "projectId", pipeline FROM "Conversation" WHERE id = $1',
            conversation_id,
        )
        if row is None:
            raise ValueError(f"Conversation {conversation_id} not found")
        return json.dumps({
            "id": row["id"],
            "title": row["title"],
            "projectId": row["projectId"],
            **_summarize(_pipeline(row)),
        })

    @mcp.resource("conversation://{conversation_id}/testcases/{tc_id}")
    async def conversation_testcase(conversation_id: str, tc_id: str) -> str:
        """Full detail of a single test case (SIL/HIL sections, standards, steps)
        from a conversation's pipeline — the drill-down behind the summary's
        testCases.ids list. Needed to build replay/modification specs."""
        pool = await _db()
        row = await pool.fetchrow('SELECT pipeline FROM "Conversation" WHERE id = $1', conversation_id)
        if row is None:
            raise ValueError(f"Conversation {conversation_id} not found")
        test_cases = (_pipeline(row).get("scenarioResult") or {}).get("testCases") or []
        for tc in test_cases:
            if tc.get("scenario_id") == tc_id:
                return json.dumps(tc)
        raise ValueError(f"Test case {tc_id} not found in conversation {conversation_id}")
