from __future__ import annotations

import asyncio
from pathlib import Path

import anyio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from backend.munder import cli
from backend.munder.eval import harness
from backend.munder.schemas import CustomerReply, RunResult, SaleResult
from backend.api import session
from backend.api.deps import current_model

router = APIRouter()


def _out_dir() -> Path:
    return Path(session.eval_db_path()).parent


@router.websocket("/ws/eval")
async def eval_ws(ws: WebSocket):
    """Run the eval harness over the sample, streaming per-request progress then the
    final rubric report."""
    await ws.accept()
    req = await ws.receive_json()
    limit = req.get("limit")
    progress_q: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_event_loop()

    model = current_model()
    base_run_fn = cli.make_run_fn(model=model)

    async def run_fn(request_text, request_date, emit):
        # Per-request resilience: one failing request must not kill the whole batch.
        try:
            return await base_run_fn(request_text, request_date, emit)
        except Exception as exc:
            return RunResult(
                request_date=request_date,
                reply=CustomerReply(text=f"[error] {exc}"[:300], fulfilled=False),
                sale=SaleResult(fulfilled=False, decline_reason=str(exc)[:200]),
            )

    def on_request(entry, rubric):
        # Called from the worker thread after each request; stream it to the UI.
        loop.call_soon_threadsafe(
            progress_q.put_nowait,
            {"type": "progress", "entry": entry, "rubric": rubric},
        )

    async with session.lock():
        session.use_eval()

        out_dir = _out_dir()

        def _run():
            return harness.run_eval(
                sample_csv=str(Path(session.data_dir()) / "quote_requests_sample.csv"),
                data_dir=session.data_dir(),
                run_fn=run_fn,
                out_dir=str(out_dir),
                judge=None,
                limit=limit,
                on_request=on_request,
            )

        task = asyncio.create_task(anyio.to_thread.run_sync(_run))
        try:
            while not task.done() or not progress_q.empty():
                try:
                    p = await asyncio.wait_for(progress_q.get(), timeout=0.05)
                except asyncio.TimeoutError:
                    continue
                await ws.send_json(p)
            report = task.result()
            session.use_live()
            await ws.send_json({"type": "report", "report": report})
        except WebSocketDisconnect:
            task.cancel()
            return
        except Exception as exc:
            session.use_live()
            try:
                await ws.send_json({"type": "error", "detail": str(exc)[:500]})
            except Exception:
                pass
    try:
        await ws.close()
    except Exception:
        pass


@router.get("/api/eval/results.csv")
def download_csv():
    return FileResponse(
        str(_out_dir() / "test_results.csv"), filename="test_results.csv"
    )
