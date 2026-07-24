"""Live test — calls the real Agent 1 on Fly.dev through the MCP tool.

Network-dependent (and the Fly machine may cold-start); expect up to a
couple of minutes. Run:  uv run python tests/live_agent1_test.py
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastmcp import Client  # noqa: E402

from server import mcp  # noqa: E402

SAMPLE = [
    "The AEB system shall detect a pedestrian crossing the road and bring the vehicle "
    "to a complete stop from 50 km/h before impact.",
    "The AEB system shall react within 300 ms of pedestrian detection.",
]


async def main() -> None:
    async with Client(mcp) as client:
        print(f"calling refine_requirements with {len(SAMPLE)} requirements (live Agent 1)…")
        result = await client.call_tool("refine_requirements", {"requirements": SAMPLE})
        output = json.loads(result.content[0].text)
        summary = output.get("summary", {})
        testable = output.get("testable", [])
        print(f"refining_id: {output.get('refining_id')}")
        print(f"summary: {json.dumps(summary)}")
        for req in testable:
            print(f"  {req.get('id')}: complexity={req.get('complexity')} "
                  f"num_scenarios={req.get('num_scenarios')} conflict={req.get('conflict_flag')}")
        assert testable or output.get("incomplete"), "expected at least one classified requirement"
        print("\nLIVE AGENT 1 TEST PASSED")


if __name__ == "__main__":
    asyncio.run(main())
