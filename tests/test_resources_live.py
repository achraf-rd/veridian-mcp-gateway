"""Live resource reads against the real Postgres (Prisma) database.

Reads a known rich conversation in-process (no port) and checks the summary
projection, a single test-case drill-down, and the project index. Requires
DATABASE_URL (resolved from the frontend .env fallback).

Run:  uv run python tests/test_resources_live.py
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastmcp import Client  # noqa: E402

from server import mcp  # noqa: E402

CONV = "cmpzntc0r0001c4ezzpwrjlk2"  # title 'testcasegen', 24 test cases, has execution
TC = "TC-req-001-01"


def _json(result) -> dict:
    for item in result:
        text = getattr(item, "text", None)
        if text:
            return json.loads(text)
    raise AssertionError("resource returned no text content")


async def main() -> None:
    async with Client(mcp) as client:
        summary = _json(await client.read_resource(f"conversation://{CONV}/summary"))
        print(f"summary: stage={summary.get('stage')} testCases={summary['testCases']['total']} "
              f"execution={summary.get('execution')} report={summary.get('report')}")
        assert summary["id"] == CONV
        assert summary["testCases"]["total"] == 24
        assert summary["execution"], "expected an execution result"
        project_id = summary["projectId"]
        # projection stays small
        assert len(json.dumps(summary)) < 4000, "summary should be a compact projection, not the raw blob"

        tc = _json(await client.read_resource(f"conversation://{CONV}/testcases/{TC}"))
        print(f"testcase {TC}: feature={tc.get('feature_under_test')} phase={tc.get('test_phase')} "
              f"has_sil={tc.get('sil_section') is not None}")
        assert tc["scenario_id"] == TC

        index = _json(await client.read_resource(f"project://{project_id}/conversations"))
        ids = [c["id"] for c in index["conversations"]]
        print(f"project index: {len(ids)} conversations, target present={CONV in ids}")
        assert CONV in ids

    print("\nLIVE RESOURCES TEST PASSED")


if __name__ == "__main__":
    asyncio.run(main())
