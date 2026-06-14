from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.munder import agents as agents_mod
from backend.munder import orchestrator
from backend.munder.events import RunEvent
from backend.munder.policies import BusinessPolicy
from backend.munder.eval.deterministic import run_all_checks
from backend.munder.eval.judge import build_judge, judge_text
from backend.api import session
from backend.api.deps import current_model
from backend.api.events_json import event_to_json, result_to_json

router = APIRouter()


@router.websocket("/ws/reception")
async def reception_ws(ws: WebSocket):
    """Stream RunEvents for a single customer request, then the final RunResult.

    Resilient to client disconnects and to orchestrator failures (e.g. a bad model
    name / API error): the error is sent to the client as an ``error`` message instead
    of crashing the handler.
    """
    await ws.accept()
    try:
        req = await ws.receive_json()
    except WebSocketDisconnect:
        return

    queue: asyncio.Queue = asyncio.Queue()

    def emit(e: RunEvent) -> None:
        queue.put_nowait(e)

    async with session.lock():
        session.use_live()
        model = current_model()
        built = agents_mod.build_agents(model=model)

        async def run():
            return await orchestrator.run_request(
                request_text=req["request_text"],
                request_date=req["request_date"],
                built=built,
                model=model,
                emit=emit,
            )

        task = asyncio.create_task(run())
        try:
            while not task.done() or not queue.empty():
                try:
                    e = await asyncio.wait_for(queue.get(), timeout=0.05)
                except asyncio.TimeoutError:
                    continue
                await ws.send_json(event_to_json(e))
            # Surface the result or the orchestrator's exception.
            result = task.result()
            # Embedded evaluation: deterministic checks + LLM judge on this request.
            await ws.send_json(await _evaluate(result, model))
            await ws.send_json(result_to_json(result))
        except WebSocketDisconnect:
            task.cancel()
            return
        except Exception as exc:  # orchestrator/LLM failure
            await _safe_send(ws, {"type": "error", "detail": str(exc)[:500]})

    await _safe_close(ws)


async def _evaluate(result, model) -> dict:
    """Embedded eval for one request: deterministic checks + an LLM judge on the reply."""
    checks = [vars(c) for c in run_all_checks(result, BusinessPolicy())]
    judge_scores = None
    try:
        scores = await judge_text(build_judge(model=model), "Michael", result.reply.text)
        judge_scores = scores.model_dump()
    except Exception:
        judge_scores = None
    return {"type": "eval", "checks": checks, "judge": judge_scores}


async def _safe_send(ws: WebSocket, payload: dict) -> None:
    try:
        await ws.send_json(payload)
    except Exception:
        pass


async def _safe_close(ws: WebSocket) -> None:
    try:
        await ws.close()
    except Exception:
        pass
