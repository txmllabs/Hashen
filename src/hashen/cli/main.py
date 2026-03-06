"""Unified CLI: hashen run | verify | bundle inspect | bundle doctor | schema list."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from hashen import __version__


def _json_out(data: object, pretty: bool) -> None:
    if pretty:
        print(json.dumps(data, sort_keys=True, indent=2))
    else:
        print(json.dumps(data, sort_keys=True, separators=(",", ":")))


def _cmd_run(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    """Run pipeline and produce bundle; output bundle path, seal hash, audit head, report path."""
    import math

    from hashen.orchestrator import run_pipeline
    from hashen.provenance.seal import verify_seal
    from hashen.utils.canonical_json import canonical_loads

    artifact_path = args.artifact_path.resolve()
    if not artifact_path.exists():
        out = {"ok": False, "error": "artifact not found", "path": str(artifact_path)}
        _json_out(out, args.pretty)
        return 1
    artifact_bytes = artifact_path.read_bytes()
    run_id = args.run_id or "run"
    h2_bins = 16
    config_vector = {
        "h2_min": 0.0,
        "h2_max": float(math.log2(h2_bins)),
        "h2_bins": h2_bins,
        "h1_subset_size": 32,
        "fixed_range_policy": "preconfigured_no_autorange",
        "policy_version": "hashen.policy.v1",
    }
    for s in args.config or []:
        if "=" in s:
            k, v = s.split("=", 1)
            try:
                config_vector[k] = float(v)
            except ValueError:
                config_vector[k] = v
    out_dir = (args.output_dir or Path(f"bundle_{run_id}")).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    result = run_pipeline(artifact_bytes, run_id, config_vector, root=out_dir)
    # Copy artifact, audit, seal into flat bundle layout
    import shutil

    (out_dir / "artifact.bin").write_bytes(artifact_bytes)
    audit_src = out_dir / "audit" / f"{run_id}.jsonl"
    if audit_src.exists():
        shutil.copy2(audit_src, out_dir / "audit.jsonl")
    seal_src = out_dir / "seals" / f"{result['artifact_digest']}.seal.json"
    if seal_src.exists():
        shutil.copy2(seal_src, out_dir / "seal.json")
    seal_record = canonical_loads(seal_src.read_text()) if seal_src.exists() else {}
    ok, reason = verify_seal(
        artifact_bytes,
        seal_record,
        audit_log_path=audit_src if audit_src.exists() else None,
    )
    verify_out = {
        "ok": ok,
        "reason": reason,
        "audit_head_hash": result["audit_head_hash"],
        "seal_hash": result["seal_hash"],
    }
    (out_dir / "verify.json").write_text(
        json.dumps(verify_out, sort_keys=True, indent=2),
    )
    from hashen import __version__ as v
    from hashen.provenance.bundle_manifest import write_bundle_manifest
    from hashen.utils.clock import utc_iso_now

    report_src = out_dir / "reports" / f"{run_id}.json"
    if report_src.exists():
        shutil.copy2(report_src, out_dir / "report.json")
    write_bundle_manifest(
        out_dir,
        created_at=utc_iso_now(),
        bundle_id=run_id,
        target_id="default",
        content_fingerprint=result["artifact_digest"],
        seal_hash_value=result["seal_hash"],
        audit_head_hash_value=result["audit_head_hash"],
        tool_version=v,
    )
    summary = {
        "ok": True,
        "bundle_path": str(out_dir),
        "seal_hash": result["seal_hash"],
        "audit_head_hash": result["audit_head_hash"],
        "report_path": str(out_dir / "report.json")
        if (out_dir / "report.json").exists()
        else str(report_src)
        if report_src.exists()
        else None,
        "verification": verify_out,
    }
    _json_out(summary, args.pretty)
    return 0


def _cmd_verify(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    """Verify bundle; output structured result (ok, seal_valid, audit_chain_valid, etc.)."""
    from hashen.verification import verify_bundle_result

    bundle_root = args.bundle_dir.resolve()
    result = verify_bundle_result(bundle_root)
    _json_out(result, args.pretty)
    return 0 if result.get("ok") else 1


def _cmd_bundle_inspect(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    """Summarize bundle contents without mutating."""
    from hashen.utils.canonical_json import canonical_loads

    root = args.bundle_dir.resolve()
    if not root.is_dir():
        _json_out({"ok": False, "error": "not a directory", "path": str(root)}, args.pretty)
        return 1
    out: dict = {"bundle_path": str(root), "files": {}}
    for name in [
        "artifact.bin",
        "artifact",
        "audit.jsonl",
        "seal.json",
        "verify.json",
        "report.json",
        "manifest.json",
    ]:
        p = root / name
        if p.exists():
            out["files"][name] = {"size": p.stat().st_size, "present": True}
    manifest_path = root / "manifest.json"
    if manifest_path.exists():
        try:
            manifest = canonical_loads(manifest_path.read_text())
            out["manifest"] = {
                "schema_version": manifest.get("schema_version"),
                "seal_hash": manifest.get("seal_hash"),
                "audit_head_hash": manifest.get("audit_head_hash"),
                "file_count": len(manifest.get("files") or {}),
            }
        except Exception as e:
            out["manifest"] = {"error": str(e)}
    seal_path = root / "seal.json"
    if seal_path.exists():
        try:
            seal = canonical_loads(seal_path.read_text())
            out["seal"] = {
                "epw_hash": seal.get("epw_hash"),
                "schema_version": seal.get("schema_version"),
            }
        except Exception as e:
            out["seal"] = {"error": str(e)}
    _json_out(out, args.pretty)
    return 0


def _cmd_bundle_doctor(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    """Run consistency checks: missing files, hash mismatches, malformed JSON, schema warnings."""
    from hashen.provenance.bundle_manifest import (
        MANIFEST_FILENAME,
        file_sha256,
    )
    from hashen.utils.canonical_json import canonical_loads

    root = args.bundle_dir.resolve()
    if not root.is_dir():
        _json_out(
            {"ok": False, "fatal": ["not a directory"], "warnings": [], "path": str(root)},
            args.pretty,
        )
        return 1
    fatal: list[str] = []
    warnings: list[str] = []
    manifest_path = root / MANIFEST_FILENAME
    if manifest_path.exists():
        try:
            manifest = canonical_loads(manifest_path.read_text())
        except Exception as e:
            fatal.append(f"malformed JSON: manifest.json: {e}")
            manifest = None
    else:
        manifest = None
        warnings.append("manifest.json missing")

    if manifest:
        files = manifest.get("files") or {}
        for name, stored_hash in files.items():
            p = root / name
            if not p.exists():
                fatal.append(f"missing file: {name}")
            elif file_sha256(p) != stored_hash:
                fatal.append(f"hash mismatch: {name}")
        schema_ver = manifest.get("schema_version")
        if schema_ver != "hashen.manifest.v1":
            warnings.append(
                f"manifest schema_version: {schema_ver!r} (expected hashen.manifest.v1)"
            )
    else:
        if not (root / "artifact.bin").exists() and not (root / "artifact").exists():
            fatal.append("missing file: artifact.bin or artifact")
        if not (root / "seal.json").exists():
            fatal.append("missing file: seal.json")

    for fname in ["seal.json", "verify.json", "report.json"]:
        p = root / fname
        if p.exists():
            try:
                canonical_loads(p.read_text())
            except Exception as e:
                fatal.append(f"malformed JSON: {fname}: {e}")

    ok = len(fatal) == 0
    _json_out({"ok": ok, "fatal": fatal, "warnings": warnings, "path": str(root)}, args.pretty)
    return 0 if ok else 1


def _cmd_schema_list(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    """Print supported schema names and versions."""
    from hashen.schemas import list_schema_names
    from hashen.schemas.loader import get_schema

    names = list_schema_names()
    out: dict = {"schemas": []}
    for name in names:
        try:
            schema = get_schema(name)
            out["schemas"].append(
                {
                    "name": name,
                    "version": schema.get("properties", {})
                    .get("schema_version", {})
                    .get("const", "N/A"),
                }
            )
        except Exception as e:
            out["schemas"].append({"name": name, "error": str(e)})
    _json_out(out, args.pretty)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="hashen", description="Hashen: deterministic provenance and evidence bundles"
    )
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    ap.add_argument("--pretty", action="store_true", help="Human-readable JSON output")
    sub = ap.add_subparsers(dest="command", required=True)

    # hashen run
    run_p = sub.add_parser("run", help="Run pipeline and produce evidence bundle")
    run_p.add_argument("artifact_path", type=Path, help="Path to artifact file")
    run_p.add_argument("run_id", nargs="?", default="run", help="Run ID")
    run_p.add_argument("--output-dir", type=Path, default=None, help="Bundle output directory")
    run_p.add_argument("--config", action="append", default=[], help="KEY=VAL config")
    run_p.set_defaults(_run=_cmd_run)

    # hashen verify
    verify_p = sub.add_parser("verify", help="Verify evidence bundle")
    verify_p.add_argument("bundle_dir", type=Path, help="Bundle directory")
    verify_p.set_defaults(_run=_cmd_verify)

    # hashen bundle inspect
    binspect_p = sub.add_parser("bundle", help="Bundle subcommands")
    binspect_sub = binspect_p.add_subparsers(dest="bundle_cmd", required=True)
    bi = binspect_sub.add_parser("inspect", help="Inspect bundle metadata")
    bi.add_argument("bundle_dir", type=Path, help="Bundle directory")
    bi.set_defaults(_run=_cmd_bundle_inspect)
    bd = binspect_sub.add_parser("doctor", help="Run bundle consistency checks")
    bd.add_argument("bundle_dir", type=Path, help="Bundle directory")
    bd.set_defaults(_run=_cmd_bundle_doctor)

    # hashen schema list
    schema_p = sub.add_parser("schema", help="Schema subcommands")
    schema_sub = schema_p.add_subparsers(dest="schema_cmd", required=True)
    sl = schema_sub.add_parser("list", help="List supported schemas and versions")
    sl.set_defaults(_run=_cmd_schema_list)

    args = ap.parse_args()
    return args._run(ap, args)


if __name__ == "__main__":
    sys.exit(main())
