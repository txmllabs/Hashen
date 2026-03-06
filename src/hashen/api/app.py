"""FastAPI service: analyze, verify, health, config."""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Optional

try:
    from fastapi import FastAPI, File, Form, Header, Request, UploadFile
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
except ImportError:
    FastAPI = None  # type: ignore[misc, assignment]

API_VERSION = "0.1.0"
SUPPORTED_MODALITIES = ["raw", "image", "audio", "text", "timeseries", "graph"]
DEFAULT_CONFIG = {
    "use_tsec": True,
    "window_size": 512,
    "h1_bins": 64,
    "h2_min": 0.0,
    "h2_max": 6.0,
    "h2_bins": 64,
    "authenticity_threshold": 4.0,
}

# In-memory rate limit: ip -> list of request timestamps (last N seconds)
_rate_limit_store: dict[str, list[float]] = {}
_rate_limit_max = int(os.environ.get("HASHEN_RATE_LIMIT_PER_MINUTE", "60"))
_rate_limit_window = 60.0


def _rate_limit_check(client_ip: str) -> bool:
    """Return True if request allowed, False if rate limited."""
    now = time.monotonic()
    if client_ip not in _rate_limit_store:
        _rate_limit_store[client_ip] = []
    times = _rate_limit_store[client_ip]
    times[:] = [t for t in times if now - t < _rate_limit_window]
    if len(times) >= _rate_limit_max:
        return False
    times.append(now)
    return True


def _api_key_ok(x_api_key: Optional[str]) -> bool:
    """If HASHEN_API_KEY is set, require X-API-Key to match; else allow."""
    env_key = os.environ.get("HASHEN_API_KEY")
    if not env_key:
        return True
    return x_api_key == env_key if x_api_key else False


def create_app() -> Any:
    """Create FastAPI app with routes and middleware."""
    if FastAPI is None:
        raise ImportError("Install optional dependency: pip install hashen[api]")

    app = FastAPI(title="Hashen API", version=API_VERSION)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.environ.get("HASHEN_CORS_ORIGINS", "*").split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    request_id_header = "X-Request-Id"

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": API_VERSION}

    @app.get("/api/v1/config")
    def config() -> dict[str, Any]:
        return {
            "supported_modalities": SUPPORTED_MODALITIES,
            "default_config": DEFAULT_CONFIG,
        }

    @app.post("/api/v1/analyze")
    async def analyze(
        request: Request,
        artifact: UploadFile = File(...),
        config_str: Optional[str] = Form(default=None, alias="config"),
        run_id: Optional[str] = Form(default=None),
        target_id: Optional[str] = Form(default="default"),
        modality: Optional[str] = Form(default="raw"),
        x_api_key: Optional[str] = Header(default=None),
    ) -> JSONResponse:
        rid = run_id or str(uuid.uuid4())
        if not _api_key_ok(x_api_key):
            return JSONResponse(
                status_code=401,
                content={"error": "unauthorized", "detail": "Invalid or missing API key"},
                headers={request_id_header: rid},
            )
        client_ip = request.client.host if request.client else "unknown"
        if not _rate_limit_check(client_ip):
            return JSONResponse(
                status_code=429,
                content={"error": "rate_limited", "detail": "Too many requests"},
                headers={request_id_header: rid},
            )
        try:
            artifact_bytes = await artifact.read()
        except Exception as e:
            return JSONResponse(
                status_code=400,
                content={"error": "bad_request", "detail": str(e)},
                headers={request_id_header: rid},
            )
        if not artifact_bytes:
            return JSONResponse(
                status_code=400,
                content={"error": "bad_request", "detail": "Empty artifact"},
                headers={request_id_header: rid},
            )
        config_vector = dict(DEFAULT_CONFIG)
        if config_str:
            try:
                config_vector.update(json.loads(config_str))
            except json.JSONDecodeError as e:
                return JSONResponse(
                    status_code=400,
                    content={"error": "bad_request", "detail": f"Invalid config JSON: {e}"},
                    headers={request_id_header: rid},
                )
        config_vector["use_tsec"] = True
        config_vector["modality"] = modality or "raw"

        root = Path.cwd()
        tmp_dir: Optional[Path] = None
        try:
            import tempfile

            tmp_dir = Path(tempfile.mkdtemp(prefix="hashen_api_"))
            root = tmp_dir
            from hashen.orchestrator import run_pipeline

            result = run_pipeline(
                artifact_bytes,
                rid,
                config_vector,
                root=root,
                target_id=target_id or "default",
            )
        except Exception as e:
            if tmp_dir and tmp_dir.exists():
                try:
                    import shutil

                    shutil.rmtree(tmp_dir, ignore_errors=True)
                except Exception:
                    pass
            return JSONResponse(
                status_code=500,
                content={"error": "internal_error", "detail": str(e)},
                headers={request_id_header: rid},
            )
        finally:
            if tmp_dir and tmp_dir.exists():
                try:
                    import shutil

                    shutil.rmtree(tmp_dir, ignore_errors=True)
                except Exception:
                    pass

        if result.get("policy_denied"):
            return JSONResponse(
                status_code=403,
                content={
                    "error": "policy_denied",
                    "detail": result.get("policy_decision", "deny"),
                },
                headers={request_id_header: rid},
            )

        response = {
            "run_id": result["run_id"],
            "seal_hash": result["seal_hash"] or "",
            "h2": result["h2"],
            "is_authentic": result["is_authentic"],
            "routing_path": result.get("routing_path") or [],
            "uncertainty": result.get("uncertainty", 0.0),
            "resonance": result.get("resonance", 0.0),
            "audit_head_hash": result["audit_head_hash"],
            "cache_hit": result.get("cache_hit", False),
            "seal_record": result.get("seal_record"),
        }
        return JSONResponse(
            status_code=200,
            content=response,
            headers={request_id_header: rid},
        )

    @app.post("/api/v1/verify")
    async def verify(
        request: Request,
        artifact: UploadFile = File(...),
        seal: Optional[str] = Form(default=None),
        seal_file: Optional[UploadFile] = File(default=None),
        audit: Optional[UploadFile] = File(default=None),
        x_api_key: Optional[str] = Header(default=None),
    ) -> JSONResponse:
        rid = str(uuid.uuid4())
        if not _api_key_ok(x_api_key):
            return JSONResponse(
                status_code=401,
                content={"error": "unauthorized", "detail": "Invalid or missing API key"},
                headers={request_id_header: rid},
            )
        if not _rate_limit_check(request.client.host if request.client else "unknown"):
            return JSONResponse(
                status_code=429,
                content={"error": "rate_limited", "detail": "Too many requests"},
                headers={request_id_header: rid},
            )
        try:
            artifact_bytes = await artifact.read()
        except Exception as e:
            return JSONResponse(
                status_code=400,
                content={"error": "bad_request", "detail": str(e)},
                headers={request_id_header: rid},
            )
        seal_record: Optional[dict[str, Any]] = None
        if seal_file and seal_file.filename:
            body = await seal_file.read()
            try:
                seal_record = json.loads(body.decode("utf-8"))
            except Exception as e:
                return JSONResponse(
                    status_code=400,
                    content={"error": "bad_request", "detail": f"Invalid seal file: {e}"},
                    headers={request_id_header: rid},
                )
        elif seal:
            try:
                seal_record = json.loads(seal)
            except Exception as e:
                return JSONResponse(
                    status_code=400,
                    content={"error": "bad_request", "detail": f"Invalid seal JSON: {e}"},
                    headers={request_id_header: rid},
                )
        if not seal_record:
            return JSONResponse(
                status_code=400,
                content={"error": "bad_request", "detail": "seal or seal_file required"},
                headers={request_id_header: rid},
            )
        # Accept full analyze response (with seal_record) or raw seal record
        seal_record = seal_record.get("seal_record") or seal_record
        audit_path = None
        if audit and audit.filename:
            audit_bytes = await audit.read()
            import tempfile

            fd, path = tempfile.mkstemp(suffix=".jsonl", prefix="hashen_audit_")
            try:
                os.write(fd, audit_bytes)
                os.close(fd)
                audit_path = Path(path)
            except Exception:
                os.close(fd)
                try:
                    os.unlink(path)
                except Exception:
                    pass

        try:
            from hashen.provenance.seal import verify_seal

            ok, reason = verify_seal(artifact_bytes, seal_record, audit_log_path=audit_path)
        finally:
            if audit_path and audit_path.exists():
                try:
                    audit_path.unlink()
                except Exception:
                    pass

        return JSONResponse(
            status_code=200,
            content={
                "ok": ok,
                "reason": reason,
                "seal_valid": ok,
                "audit_chain_valid": None if audit_path is None else ok,
            },
            headers={request_id_header: rid},
        )

    return app


app = create_app() if FastAPI is not None else None


def run_server() -> None:
    """Entry point for hashen-api script: run uvicorn."""
    import uvicorn

    uvicorn.run(
        "hashen.api.app:app",
        host=os.environ.get("HASHEN_HOST", "0.0.0.0"),
        port=int(os.environ.get("HASHEN_PORT", "8000")),
        reload=os.environ.get("HASHEN_RELOAD", "").lower() in ("1", "true", "yes"),
    )
