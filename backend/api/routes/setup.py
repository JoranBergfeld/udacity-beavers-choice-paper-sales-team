from __future__ import annotations

from fastapi import APIRouter

from backend.api.config import CONFIG
from backend.api.models import ConfigUpdate, SeedRequest
from backend.api import session

router = APIRouter()


@router.get("/config")
def get_config():
    return CONFIG.public_dict()


@router.put("/config")
def put_config(update: ConfigUpdate):
    if update.model is not None:
        CONFIG.model = update.model
    if update.base_url is not None:
        CONFIG.base_url = update.base_url
    return CONFIG.public_dict()


@router.get("/status")
def status():
    return {"db_seeded": session.db_seeded(), "demo_mode": CONFIG.demo_mode}


@router.post("/seed")
def seed(req: SeedRequest):
    session.seed_live(reset=req.reset)
    return {"db_seeded": True}


@router.post("/test-connection")
def test_connection():
    if CONFIG.demo_mode:
        return {
            "ok": True,
            "demo_mode": True,
            "detail": "No API key set. Running in demo mode (TestModel).",
        }
    from pydantic_ai import Agent

    from backend.munder.agents import build_model

    try:
        agent = Agent(build_model(), output_type=str)
        import anyio

        anyio.run(lambda: agent.run("ping"))
        return {"ok": True, "demo_mode": False}
    except Exception as e:
        return {"ok": False, "demo_mode": False, "detail": str(e)[:200]}
