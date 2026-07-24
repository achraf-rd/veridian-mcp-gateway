"""MCP prompts — the 4 smart-routing flow templates (Lane 3).

Surfaced to engineers as composer slash commands (/pipeline, /direct,
/replay, /reevaluate); the orchestrator fills them via prompts/get.
Prompt args are strings by MCP spec.
"""

from fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    @mcp.prompt
    def full_pipeline(requirements: str) -> str:
        """Run the full validation pipeline on a batch of raw requirements."""
        return (
            "Run the full Veridian validation pipeline on these raw requirements:\n\n"
            f"{requirements}\n\n"
            "(1) call refine_requirements, (2) PAUSE at the requirements gate for "
            "engineer approval, (3) pass only status=='valid' items to "
            "generate_test_cases, (4) PAUSE at the test-case gate, (5) build "
            "ScenarioSpecs and call generate_xosc, (6) PAUSE at the XOSC gate, "
            "(7) execute_simulation, then evaluate_results."
        )

    @mcp.prompt
    def direct_testcase(scenario_description: str) -> str:
        """Generate a scenario file directly from one test-case description, skipping refinement."""
        return (
            f"Generate a scenario directly for: {scenario_description}\n\n"
            "Format the description into a single ScenarioSpec and call generate_xosc "
            "for it only. Do NOT run refine_requirements or generate_test_cases. "
            "Persist the result and pause at the XOSC approval gate."
        )

    @mcp.prompt
    def replay_with_mods(test_case_id: str, modifications: str) -> str:
        """Replay an existing test case with modified conditions."""
        return (
            f"Replay {test_case_id} with modifications: {modifications}.\n\n"
            f"(1) load {test_case_id} via the conversation testcases resource, "
            "(2) merge the modifications into its environment/actors, "
            "(3) call generate_xosc for the modified spec only, "
            "(4) call execute_simulation, then evaluate_results. "
            "Do NOT re-run refine_requirements or generate_test_cases. "
            "Pause at the XOSC approval gate."
        )

    @mcp.prompt
    def reevaluate(run_id: str, new_criteria: str) -> str:
        """Re-evaluate a past run's telemetry against new pass/fail criteria."""
        return (
            f"Re-evaluate run {run_id} with new criteria: {new_criteria}.\n\n"
            "(1) load the run's execution result from the conversation resource, "
            "(2) apply the new criteria as evaluation overrides, "
            "(3) call evaluate_results only. Do NOT re-generate or re-execute "
            "any scenario."
        )
