from __future__ import annotations

# Load .env BEFORE anything reads os.environ (config.py checks the API key at import).
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_app() -> FastAPI:
    app = FastAPI(title="Munder Difflin")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    from backend.api.routes import setup, knowledge, financials, reception, evaluation

    app.include_router(setup.router, prefix="/api")
    app.include_router(knowledge.router, prefix="/api")
    app.include_router(financials.router, prefix="/api")
    app.include_router(reception.router)
    app.include_router(evaluation.router)
    return app


app = create_app()
