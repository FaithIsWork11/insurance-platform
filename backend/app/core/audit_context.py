from __future__ import annotations

from typing import Any
from fastapi import Request


def get_client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    if request.client and request.client.host:
        return request.client.host

    return None


def build_audit_context(request: Request) -> dict[str, Any]:
    return {
        "request_id": getattr(request.state, "request_id", None),
        "ip_address": get_client_ip(request),
        "endpoint_path": request.url.path,
        "http_method": request.method,
    }