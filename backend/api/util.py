from __future__ import annotations

import math
from typing import Any


def json_safe(obj: Any) -> Any:
    """Recursively replace NaN/inf floats with None so Starlette's JSON encoder
    (which uses allow_nan=False) can serialize DB-derived reports.

    NaN shows up in financial reports because the seed opening-balance row has a
    NULL item_name/units; once mixed with real sales, pandas yields a float column
    containing NaN.
    """
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, dict):
        return {k: json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [json_safe(v) for v in obj]
    return obj
