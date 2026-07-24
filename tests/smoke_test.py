"""In-memory smoke test — no port binding, no network to the agents.

Exercises the MCP surface via FastMCP's in-process client: lists the three
primitives, fills a prompt, and calls the two stub tools end-to-end.
Run from the gateway root:  uv run python tests/smoke_test.py
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastmcp import Client  # noqa: E402

from server import mcp  # noqa: E402


async def main() -> None:
    async with Client(mcp) as client:
        tools = await client.list_tools()
        names = sorted(t.name for t in tools)
        expected = sorted([
            "refine_requirements", "generate_test_cases", "generate_xosc",
            "execute_simulation", "evaluate_results", "stop_agent",
        ])
        assert names == expected, f"tools mismatch: {names}"
        print(f"tools/list OK — {names}")

        prompts = await client.list_prompts()
        prompt_names = sorted(p.name for p in prompts)
        assert prompt_names == ["direct_testcase", "full_pipeline", "reevaluate", "replay_with_mods"], prompt_names
        print(f"prompts/list OK — {prompt_names}")

        filled = await client.get_prompt(
            "replay_with_mods", {"test_case_id": "TC#042", "modifications": "night + fog"}
        )
        text = filled.messages[0].content.text
        assert "TC#042" in text and "night + fog" in text
        print("prompts/get OK — replay_with_mods fills arguments")

        templates = await client.list_resource_templates()
        uris = sorted(t.uriTemplate for t in templates)
        print(f"resources/templates OK — {uris}")
        assert any("conversation://" in u for u in uris) and any("project://" in u for u in uris)

        # execute_simulation is now the REAL Agent 4 (executor-agent.fly.dev). Call
        # it with no scenarios so this stays offline — proves the tool shape without
        # hitting the executor (see tests/live_agent4_test.py for a real run).
        exec_result = await client.call_tool("execute_simulation", {"scenarios": []})
        execution = json.loads(exec_result.content[0].text)
        assert execution == {"total": 0, "passed": 0, "failed": 0, "runs": []}, execution
        print("tools/call OK — execute_simulation reachable (real Agent 4, 0 scenarios)")

        report_result = await client.call_tool("evaluate_results", {"execution": {"total": 2, "passed": 2}})
        report = json.loads(report_result.content[0].text)
        assert report["verdict"] == "pass" and report["kpis"]
        print(f"tools/call OK — evaluate_results: verdict={report['verdict']} score={report['score']} (stub)")

    print("\nSMOKE TEST PASSED")


if __name__ == "__main__":
    asyncio.run(main())
