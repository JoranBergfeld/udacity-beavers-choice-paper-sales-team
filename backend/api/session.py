from __future__ import annotations

import asyncio
import os
from pathlib import Path

from backend.munder import db

_lock = asyncio.Lock()


def live_db_path() -> str:
    return os.environ.get("MUNDER_LIVE_DB", "munder_live.db")


def eval_db_path() -> str:
    return os.environ.get("MUNDER_EVAL_DB", "munder_eval.db")


def data_dir() -> str:
    return str(Path(db.__file__).parent / "data")


def use_live() -> None:
    """Point the global DB engine at the live (Reception/Knowledge) database."""
    db.configure(live_db_path())


def use_eval() -> None:
    """Point the global DB engine at the isolated eval database."""
    db.configure(eval_db_path())


def db_seeded() -> bool:
    """True if the live DB has been initialized (inventory table populated)."""
    use_live()
    try:
        import pandas as pd

        return not pd.read_sql("SELECT 1 FROM inventory LIMIT 1", db.db_engine).empty
    except Exception:
        return False


def seed_live(reset: bool = True) -> None:
    """(Re)initialize the live DB with cash $50k + seed-137 inventory."""
    use_live()
    db.init_database(data_dir=data_dir(), seed=137)


def lock() -> asyncio.Lock:
    """Serializes access to the process-global DB engine across requests/eval runs."""
    return _lock


# Default the engine to the live DB at import so any early call is sane.
use_live()
