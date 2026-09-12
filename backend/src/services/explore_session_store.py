"""In-memory exploration sessions (no DB migration needed).

Single-process precedent: execution queues in src/execution/listener.py.

Deploy constraint: sessions live in process memory. Under multi-worker
uvicorn (or multiple replicas) a poll routed to another worker returns
404. Run a single worker (or add sticky sessions / shared store) when
using page exploration.
"""

import asyncio
import time
from typing import Any, Optional

from src.core.llm_provider import LLMProvider
from src.models.base import generate_uuid
from src.services.page_agent_service import PageAgentService

SESSION_TTL_SEC = 30 * 60
MAX_SESSIONS = 100

_sessions: dict[str, dict] = {}


def _prune() -> None:
    now = time.time()
    expired = [sid for sid, s in _sessions.items() if now - s.get("created_at", now) > SESSION_TTL_SEC]
    for sid in expired:
        _sessions.pop(sid, None)
    while len(_sessions) > MAX_SESSIONS:
        oldest = min(_sessions, key=lambda k: _sessions[k].get("created_at", 0))
        _sessions.pop(oldest, None)


def create_session(case_id: str, url: str, goals: list[str]) -> dict:
    _prune()
    sid = generate_uuid()
    _sessions[sid] = {
        "session_id": sid,
        "case_id": case_id,
        "url": url,
        "goals": goals,
        "status": "running",
        "steps": 0,
        "log": [],
        "catalog": [],
        "note": "",
        "created_at": time.time(),
    }
    return _sessions[sid]


def get_session(session_id: str) -> Optional[dict]:
    _prune()
    return _sessions.get(session_id)


async def _run_explore(
    session_id: str,
    url: str,
    goals: list[str],
    credentials: dict[str, str],
    provider: LLMProvider,
    max_steps: int,
) -> None:
    session = _sessions.get(session_id)
    if not session:
        return

    async def on_step(step: dict) -> None:
        session["steps"] = step.get("step", session["steps"])
        session["log"].append(step)
        session["log"] = session["log"][-20:]

    try:
        agent = PageAgentService(provider=provider, max_steps=max_steps)
        result = await agent.explore(url, goals, credentials, on_step=on_step)
        session["status"] = result.get("status", "error")
        session["catalog"] = result.get("catalog", [])
        session["note"] = result.get("note", "")
    except Exception as exc:
        session["status"] = "error"
        session["note"] = f"探索發生未預期錯誤：{exc}"
    finally:
        session["steps"] = max(session["steps"], 0)


def launch_explore_session(
    case_id: str,
    url: str,
    goals: list[str],
    credentials: dict[str, str],
    provider: LLMProvider,
    max_steps: int,
) -> dict:
    session = create_session(case_id, url, goals)
    asyncio.create_task(_run_explore(
        session["session_id"], url, goals, credentials, provider, max_steps,
    ))
    return session


def public_view(session: dict) -> dict[str, Any]:
    return {
        "session_id": session["session_id"],
        "case_id": session["case_id"],
        "url": session["url"],
        "status": session["status"],
        "steps": session["steps"],
        "log": session["log"],
        "catalog": session["catalog"],
        "note": session["note"],
    }
