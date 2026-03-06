"""Load and validate Hashen artifacts against JSON Schemas."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import jsonschema
except ImportError:
    jsonschema = None  # type: ignore[assignment]

_SCHEMA_NAMES = (
    "seal",
    "report",
    "bundle",
    "audit_event",
    "verification_result",
)


def _schema_dir() -> Path:
    """Return directory containing .schema.json files (package or repo)."""
    # Package: hashen/schemas/loader.py -> hashen/schemas/
    pkg_schemas = Path(__file__).resolve().parent
    if (pkg_schemas / "seal.schema.json").exists():
        return pkg_schemas
    # Repo root schemas/
    repo_schemas = pkg_schemas.parent.parent.parent / "schemas"
    if repo_schemas.exists():
        return repo_schemas
    return pkg_schemas


def _load_schema(name: str) -> dict[str, Any]:
    """Load a schema by short name (seal, report, bundle, audit_event, verification_result)."""
    base = name.replace(".schema.json", "")
    path = _schema_dir() / f"{base}.schema.json"
    if not path.exists():
        raise FileNotFoundError(f"Schema not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def get_schema(name: str) -> dict[str, Any]:
    """Return the JSON Schema dict for the given name."""
    return _load_schema(name)


def list_schema_names() -> list[str]:
    """Return list of supported schema short names."""
    return list(_SCHEMA_NAMES)


def validate_seal(data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate a seal record. Returns (valid, list of error messages)."""
    if jsonschema is None:
        return True, []
    try:
        jsonschema.validate(instance=data, schema=_load_schema("seal"))
        return True, []
    except jsonschema.ValidationError as e:
        return False, [str(e)]
    except jsonschema.SchemaError as e:
        return False, [str(e)]


def validate_report(data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate a compliance report. Returns (valid, list of error messages)."""
    if jsonschema is None:
        return True, []
    try:
        jsonschema.validate(instance=data, schema=_load_schema("report"))
        return True, []
    except jsonschema.ValidationError as e:
        return False, [str(e)]
    except jsonschema.SchemaError as e:
        return False, [str(e)]


def validate_bundle_manifest(data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate a bundle manifest. Returns (valid, list of error messages)."""
    if jsonschema is None:
        return True, []
    try:
        jsonschema.validate(instance=data, schema=_load_schema("bundle"))
        return True, []
    except jsonschema.ValidationError as e:
        return False, [str(e)]
    except jsonschema.SchemaError as e:
        return False, [str(e)]


def validate_audit_event(data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate a single audit event. Returns (valid, list of error messages)."""
    if jsonschema is None:
        return True, []
    try:
        jsonschema.validate(instance=data, schema=_load_schema("audit_event"))
        return True, []
    except jsonschema.ValidationError as e:
        return False, [str(e)]
    except jsonschema.SchemaError as e:
        return False, [str(e)]


def validate_verification_result(data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate a verification result object. Returns (valid, list of error messages)."""
    if jsonschema is None:
        return True, []
    try:
        jsonschema.validate(instance=data, schema=_load_schema("verification_result"))
        return True, []
    except jsonschema.ValidationError as e:
        return False, [str(e)]
    except jsonschema.SchemaError as e:
        return False, [str(e)]
