"""Lightweight timing logs for the gateway — one line per tool call to stdout
(the gateway terminal), e.g.:

    12:03:41 [perf] tool:refine_requirements   6120ms  n=3
    12:03:49 [perf] tool:generate_test_cases  41880ms  reqs=1

Shows which upstream agent is eating the time (Agents 1/2/3 are remote Fly/Dokploy
services, so a big number here = that agent/network, not the gateway).
"""

import logging
import sys
import time
from contextlib import asynccontextmanager

logger = logging.getLogger("gateway.perf")


def setup_logging(level: int = logging.INFO) -> None:
    if logger.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s [perf] %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False


def log(event: str, ms: float, **fields) -> None:
    extra = " ".join(f"{k}={v}" for k, v in fields.items() if v is not None)
    logger.info(f"{event:<26} {ms:8.0f}ms  {extra}")


@asynccontextmanager
async def timed(event: str, **fields):
    t0 = time.perf_counter()
    try:
        yield
    finally:
        log(event, (time.perf_counter() - t0) * 1000, **fields)
