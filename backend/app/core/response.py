from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlencode

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def build_meta(request: Optional[Request] = None, extra: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    rid = str(uuid.uuid4())
    if request is not None and hasattr(request.state, "request_id"):
        rid = request.state.request_id

    m: dict[str, Any] = {
        "request_id": rid,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if request is not None:
        m["path"] = request.url.path
        m["method"] = request.method

    if extra:
        for k, v in extra.items():
            if v is not None:
                m[k] = v

    return m


def ok(
    *,
    request: Optional[Request],
    data: Any,
    meta_extra: Optional[dict[str, Any]] = None,
    meta: Optional[dict[str, Any]] = None,     # ✅ alias for older call sites
    status_code: int = 200,
    flatten_keys: Optional[list[str]] = None,  # ✅ ENTERPRISE: expose selected data keys at top level
) -> JSONResponse:
    merged: dict[str, Any] = {}
    if meta_extra:
        merged.update(meta_extra)
    if meta:
        merged.update(meta)

    payload: dict[str, Any] = {"ok": True, "meta": build_meta(request, merged), "data": data}

    # ✅ enterprise: compatibility mode for tests/legacy clients
    if flatten_keys and isinstance(data, dict):
        for k in flatten_keys:
            if k in data:
                payload[k] = data[k]

    return JSONResponse(status_code=status_code, content=jsonable_encoder(payload))


def fail(
    *,
    request: Optional[Request],
    code: str,
    message: str,
    fields: Any = None,
    meta_extra: Optional[dict[str, Any]] = None,
    meta: Optional[dict[str, Any]] = None,   # ✅ alias
    status_code: int = 400,
) -> JSONResponse:
    merged: dict[str, Any] = {}
    if meta_extra:
        merged.update(meta_extra)
    if meta:
        merged.update(meta)

    payload = {
        "ok": False,
        "meta": build_meta(request, merged),
        "error": {"code": code, "message": message, "fields": fields},
    }
    return JSONResponse(status_code=status_code, content=jsonable_encoder(payload))


def paged(
    *,
    request: Optional[Request],
    items: list[Any],
    page: int,
    page_size: int,
    total: int,
    meta_extra: Optional[dict[str, Any]] = None,
    meta: Optional[dict[str, Any]] = None,   # ✅ alias
    extra_query: Optional[dict[str, Any]] = None,
    status_code: int = 200,
) -> JSONResponse:
    pages = (total + page_size - 1) // page_size if page_size else 0

    def build_url(target_page: int) -> Optional[str]:
        if request is None:
            return None
        if target_page < 1 or (pages and target_page > pages):
            return None

        q = dict(request.query_params)
        q["page"] = target_page
        q["page_size"] = page_size
        if extra_query:
            q.update({k: v for k, v in extra_query.items() if v is not None})

        return f"{request.url.path}?{urlencode(q, doseq=True)}"

    payload = {
        "items": items,
        "paging": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": pages,
            "next": build_url(page + 1),
            "prev": build_url(page - 1),
        },
    }

    return ok(request=request, data=payload, meta_extra=meta_extra, meta=meta, status_code=status_code)