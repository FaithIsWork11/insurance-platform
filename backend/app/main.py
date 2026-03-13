from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from dotenv import load_dotenv

import uuid
from datetime import datetime, timezone

from app.core.app_error import AppError
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.leads import router as leads_router
from app.routers.audit_logs import router as audit_logs_router
from app.core.request_id import RequestIdMiddleware
from app.core.response import ok


load_dotenv()

app = FastAPI(title="Insurance Platform")


# -----------------------------
# Enterprise Meta Helper
# -----------------------------
def _meta(request: Request | None = None):
    rid = str(uuid.uuid4())

    if request and hasattr(request.state, "request_id"):
        rid = request.state.request_id

    m = {
        "request_id": rid,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if request:
        m["path"] = request.url.path
        m["method"] = request.method

    return m


def _safe_body(body):
    """
    Ensure request body is JSON-serializable.
    Prevents 'bytes is not JSON serializable' crashes.
    """
    if body is None:
        return None
    if isinstance(body, (bytes, bytearray)):
        try:
            return body.decode("utf-8", errors="replace")
        except Exception:
            return repr(body)
    return body


# -----------------------------
# Enterprise Error Handlers
# -----------------------------
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    payload = {
        "ok": False,
        "meta": _meta(request),
        "error": {
            "code": exc.code,
            "message": exc.message,
            "fields": exc.fields,
        },
    }
    return JSONResponse(status_code=exc.status_code, content=jsonable_encoder(payload))


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    payload = {
        "ok": False,
        "meta": _meta(request),
        "error": {
            "code": f"HTTP_{exc.status_code}",
            "message": exc.detail if isinstance(exc.detail, str) else "Request failed",
        },
    }
    return JSONResponse(status_code=exc.status_code, content=jsonable_encoder(payload))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    payload = {
        "ok": False,
        "meta": _meta(request),
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "fields": exc.errors(),
        },
        "body": _safe_body(getattr(exc, "body", None)),
    }
    return JSONResponse(status_code=422, content=jsonable_encoder(payload))


# -----------------------------
# Middleware
# -----------------------------
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request.state.request_id = str(uuid.uuid4())
    response = await call_next(request)
    return response


app.add_middleware(RequestIdMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# Routers + Static
# -----------------------------
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(leads_router)
app.include_router(audit_logs_router)
# -----------------------------
# Health / Root
# -----------------------------
@app.get("/")
def root(request: Request):
    return ok(request=request, data={"message": "API is running. Try /docs"})


@app.get("/health")
def health(request: Request):
    return ok(request=request, data={"status": "healthy"})