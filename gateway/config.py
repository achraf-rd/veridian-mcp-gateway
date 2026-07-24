import os
from pathlib import Path

from dotenv import load_dotenv

# Local gateway .env first, then fill gaps from the sibling Veridian_frontend/.env
# (which already holds DATABASE_URL + the agent URLs).
load_dotenv()
_frontend_env = Path(__file__).resolve().parents[2] / "Veridian_frontend" / ".env"
if _frontend_env.exists():
    load_dotenv(_frontend_env, override=False)

# Dokploy deployment (gpt-oss-20b, fast). Replaces the old adas-req-refiner.fly.dev
# (gpt-oss-120b, severely queued) the orchestrator was still hitting via this default.
AGENT1_URL = os.getenv("AGENT1_URL", "https://reqsrefineragent.achrafrachid.com").rstrip("/")
AGENT2_URL = os.getenv("AGENT2_URL", "https://agenticve-testing.fly.dev").rstrip("/")
AGENT3_URL = os.getenv("AGENT3_URL", "https://adas-scenarios-gen.fly.dev").rstrip("/")
# Agent 4 — ADAS Scenario Executor (eSMini → report + MCAP). Same default the
# frontend uses (src/lib/executor.ts).
EXECUTOR_URL = os.getenv("EXECUTOR_URL", "https://executor-agent.fly.dev").rstrip("/")
DATABASE_URL = os.getenv("DATABASE_URL")

GATEWAY_HOST = os.getenv("GATEWAY_HOST", "127.0.0.1")
GATEWAY_PORT = int(os.getenv("GATEWAY_PORT", "8100"))
