"""Pydantic models for API request/response validation."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class AnalyzeResponse(BaseModel):
    """Response for POST /api/v1/analyze."""

    run_id: str
    seal_hash: str
    h2: float
    is_authentic: bool
    routing_path: list[str]
    uncertainty: float
    resonance: float
    audit_head_hash: str
    cache_hit: bool
    seal_record: Optional[dict] = Field(default=None, description="Full seal for verify")


class VerifyResponse(BaseModel):
    """Response for POST /api/v1/verify."""

    ok: bool
    reason: Optional[str] = None
    seal_valid: bool
    audit_chain_valid: Optional[bool] = None


class HealthResponse(BaseModel):
    """Response for GET /api/v1/health."""

    status: str = "ok"
    version: str = "0.1.0"


class ConfigResponse(BaseModel):
    """Response for GET /api/v1/config."""

    supported_modalities: list[str]
    default_config: dict


class ErrorResponse(BaseModel):
    """Error response body."""

    error: str
    detail: str
