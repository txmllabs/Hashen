"""Unified CLI: hashen run | verify | bundle inspect | bundle doctor | schema list."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from pathlib import Path

from hashen import __version__
from hashen.orchestrator import run_pipeline
from hashen.provenance.bundle_manifest import write_bundle_manifest
from hashen.provenance.seal import verify_seal
from hashen.utils.canonical_json import canonical_loads
from hashen.utils.clock import utc_iso_now


def _json_out(data: object, pretty: bool) -> None:
    if pretty:
        print(json.dumps(data, sort_keys=True, indent=2))
    else:
        print(json.dumps(data, sort_keys=True, separators=(",", ":")))


def _cmd_run(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    """Run pipeline and produce bundle; output bundle path, seal hash, audit head, report path."""
    artifact_path = args.artifact_path.resolve()
    if not artifact_path.exists():
        out = {"ok": False, "error": "artifact not found", "path": str(artifact_path)}
        _json_out(out, args.pretty)
        return 1
    artifact_bytes = artifact_path.read_bytes()
    run_id = args.run_id or "run"
    bundle_id = args.bundle_id or run_id
    target_id = args.target_id or "default"
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
    result = run_pipeline(
        artifact_bytes,
        run_id,
        config_vector,
        root=out_dir,
        target_id=target_id,
    )
    # Copy artifact, audit, seal into flat bundle layout
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
    report_src = out_dir / "reports" / f"{run_id}.json"
    if report_src.exists():
        shutil.copy2(report_src, out_dir / "report.json")
    write_bundle_manifest(
        out_dir,
        created_at=utc_iso_now(),
        bundle_id=bundle_id,
        target_id=target_id,
        content_fingerprint=result["artifact_digest"],
        seal_hash_value=result["seal_hash"],
        audit_head_hash_value=result["audit_head_hash"],
        tool_version=__version__,
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
    """Run consistency checks via unified verification, plus doctor-specific advisories."""
    from hashen.utils.canonical_json import canonical_loads
    from hashen.verification import verify_bundle

    root = args.bundle_dir.resolve()
    result = verify_bundle(root)

    fatal: list[str] = list(result.errors)
    warnings: list[str] = list(result.warnings)

    # Doctor-specific: legal_hold advisory from report (not covered by unified verification)
    report_path = root / "report.json"
    if report_path.exists():
        try:
            data = canonical_loads(report_path.read_text())
            ret = (data.get("retention") or data.get("compliance")) or {}
            if ret.get("legal_hold") is True:
                warnings.append("legal_hold: bundle not deletable")
        except Exception:
            pass  # already in fatal if malformed from verify_bundle

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


def _cmd_exec_validate(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    """Validate a Python script against restricted execution policy (best-effort)."""
    from hashen.sandbox.posture import SecurityPosture, default_posture
    from hashen.sandbox.validation import validate_source

    script_path = args.script_path.resolve()
    if not script_path.exists():
        _json_out({"ok": False, "error": "script not found", "path": str(script_path)}, args.pretty)
        return 1
    source = script_path.read_text(encoding="utf-8")

    posture = default_posture()
    overrides: dict[str, object] = {"mode": args.mode}
    if args.allow_network:
        overrides["allow_network"] = True
    if args.allow_filesystem_write:
        overrides["allow_filesystem_write"] = True
    if args.allow_subprocess_spawn:
        overrides["allow_subprocess_spawn"] = True
    if args.allow_import:
        overrides["allowed_imports"] = posture.allowed_imports.union(set(args.allow_import))
    if args.max_runtime_seconds is not None:
        overrides["max_runtime_seconds"] = float(args.max_runtime_seconds)
    if args.max_output_bytes is not None:
        overrides["max_output_bytes"] = int(args.max_output_bytes)

    posture = SecurityPosture(**{**posture.__dict__, **overrides})
    ok, violations = validate_source(source, posture)
    out = {
        "ok": ok,
        "mode": posture.mode,
        "violations": [v.to_dict() for v in violations],
        "limits": {
            "max_source_bytes": posture.max_source_bytes,
            "max_ast_nodes": posture.max_ast_nodes,
        },
        "posture": {
            "allow_network": posture.allow_network,
            "allow_filesystem_write": posture.allow_filesystem_write,
            "allow_subprocess_spawn": posture.allow_subprocess_spawn,
            "allowed_imports": sorted(posture.allowed_imports),
            "max_runtime_seconds": posture.max_runtime_seconds,
            "max_output_bytes": posture.max_output_bytes,
            "max_memory_mb": posture.max_memory_mb,
            "max_cpu_seconds": posture.max_cpu_seconds,
        },
        "security_notes": [
            "Validation is best-effort and not a security boundary.",
            "Use OS/container isolation for untrusted code.",
        ],
    }
    _json_out(out, args.pretty)
    return 0 if ok else 1


def _cmd_exec_run(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    """Run a script in configured restricted-execution mode (best-effort)."""
    from hashen.sandbox import SubprocessRunner
    from hashen.sandbox.posture import SecurityPosture, default_posture

    script_path = args.script_path.resolve()
    if not script_path.exists():
        _json_out({"ok": False, "error": "script not found", "path": str(script_path)}, args.pretty)
        return 1
    source = script_path.read_text(encoding="utf-8")

    posture = default_posture()
    overrides: dict[str, object] = {"mode": args.mode}
    if args.allow_network:
        overrides["allow_network"] = True
    if args.allow_filesystem_write:
        overrides["allow_filesystem_write"] = True
    if args.allow_subprocess_spawn:
        overrides["allow_subprocess_spawn"] = True
    if args.allow_import:
        overrides["allowed_imports"] = posture.allowed_imports.union(set(args.allow_import))
    if args.max_runtime_seconds is not None:
        overrides["max_runtime_seconds"] = float(args.max_runtime_seconds)
    if args.max_output_bytes is not None:
        overrides["max_output_bytes"] = int(args.max_output_bytes)

    posture = SecurityPosture(**{**posture.__dict__, **overrides})

    runner = SubprocessRunner(
        max_cpu_seconds=posture.max_cpu_seconds,
        max_mem_mb=posture.max_memory_mb,
    )
    result = runner.run_script(
        source,
        timeout_sec=float(args.timeout_sec),
        strict_mode=args.strict_mode,
        max_stdout_bytes=posture.max_output_bytes,
        mode=posture.mode,
        security_posture=posture.__dict__,
    )
    _json_out(result, args.pretty)
    return 0 if result.get("ok") else 1


def _cmd_exec_explain_policy(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    """Print effective policy posture and blocked features (best-effort summary)."""
    from hashen.sandbox.posture import default_posture

    posture = default_posture()
    out = {
        "mode": posture.mode,
        "posture": {
            "allow_network": posture.allow_network,
            "allow_filesystem_write": posture.allow_filesystem_write,
            "allow_subprocess_spawn": posture.allow_subprocess_spawn,
            "allowed_imports": sorted(posture.allowed_imports),
            "max_runtime_seconds": posture.max_runtime_seconds,
            "max_output_bytes": posture.max_output_bytes,
            "max_memory_mb": posture.max_memory_mb,
            "max_cpu_seconds": posture.max_cpu_seconds,
        },
        "blocked": {
            "builtins": [
                "eval",
                "exec",
                "compile",
                "open",
                "input",
                "__import__",
                "globals",
                "locals",
                "vars",
                "dir",
                "getattr",
                "setattr",
                "delattr",
            ],
            "reflection": ["__class__", "__mro__", "__subclasses__", "dunder attribute access"],
        },
        "security_notes": [
            "This is restricted execution, not a secure sandbox.",
            "AST checks can be bypassed by a determined attacker; "
            "use OS/container isolation for untrusted code.",
        ],
    }
    _json_out(out, args.pretty)
    return 0


def _cmd_policy_check(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    """Evaluate policy for a bundle or input context; return allow/warn/deny."""
    from hashen.compliance.models import RunContext
    from hashen.compliance.policy import evaluate as policy_evaluate

    ctx: RunContext
    bundle_dir = getattr(args, "bundle_dir", None)
    if bundle_dir is not None and Path(bundle_dir).exists():
        import json

        root = Path(bundle_dir).resolve()
        report_path = root / "report.json"
        if not report_path.exists():
            _json_out(
                {"decision": "deny", "error": "report.json not found", "path": str(root)},
                args.pretty,
            )
            return 1
        try:
            data = json.loads(report_path.read_text(encoding="utf-8"))
        except Exception as e:
            _json_out({"decision": "deny", "error": str(e)}, args.pretty)
            return 1
        comp = data.get("compliance") or data.get("retention") or {}
        ret = data.get("retention") or {}
        privacy = data.get("privacy") or {}
        ctx = RunContext(
            run_id=data.get("run_id", ""),
            retention_raw_ttl_hours=ret.get("raw_ttl_hours"),
            retention_derived_ttl_days=ret.get("derived_ttl_days"),
            legal_hold=ret.get("legal_hold", False),
            data_classification=comp.get("data_classification"),
            data_source_type=privacy.get("data_source_type") or comp.get("data_source_type"),
            pii_present=privacy.get("pii_present") or comp.get("pii_presence"),
            consent_basis=privacy.get("consent_basis") or comp.get("consent_basis"),
            purpose_of_processing=comp.get("purpose_of_processing"),
            sharing_restrictions=comp.get("sharing_restrictions"),
            action=getattr(args, "action", "run"),
            strictness=getattr(args, "strictness", "standard"),
        )
    else:
        ctx = RunContext(
            run_id=getattr(args, "run_id", "") or "cli",
            retention_raw_ttl_hours=getattr(args, "retention_raw_ttl_hours", None),
            retention_derived_ttl_days=getattr(args, "retention_derived_ttl_days", None),
            legal_hold=getattr(args, "legal_hold", False),
            data_classification=getattr(args, "data_classification", None),
            data_source_type=getattr(args, "data_source_type", None),
            pii_present=getattr(args, "pii_present", None),
            consent_basis=getattr(args, "consent_basis", None),
            purpose_of_processing=getattr(args, "purpose_of_processing", None),
            sharing_restrictions=getattr(args, "sharing_restrictions", None),
            action=getattr(args, "action", "run"),
            strictness=getattr(args, "strictness", "standard"),
        )
    result = policy_evaluate(ctx)
    out = result.to_dict()
    _json_out(out, args.pretty)
    return 0 if result.allowed else 1


def _cmd_policy_explain(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    """Print decision reasoning and triggered rules."""
    return _cmd_policy_check(parser, args)


def _cmd_retention_status(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    """Show lifecycle state, legal-hold status, retention window, policy notes."""
    from hashen.compliance.lifecycle import retention_status

    path = getattr(args, "bundle_dir", None) or getattr(args, "path", None)
    if path is None:
        _json_out({"error": "bundle_dir or path required"}, args.pretty)
        return 1
    path = Path(path).resolve()
    status = retention_status(
        path,
        raw_ttl_hours=getattr(args, "raw_ttl_hours", 24),
        derived_ttl_days=getattr(args, "derived_ttl_days", 365),
        legal_hold=getattr(args, "legal_hold", False),
    )
    _json_out(status, args.pretty)
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
    run_p.add_argument("--target-id", type=str, default="default", help="Target identifier")
    run_p.add_argument(
        "--bundle-id",
        type=str,
        default=None,
        help="Bundle identifier stored in manifest (default: run_id)",
    )
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

    # hashen policy check / explain
    policy_p = sub.add_parser("policy", help="Policy subcommands")
    policy_sub = policy_p.add_subparsers(dest="policy_cmd", required=True)
    pcheck = policy_sub.add_parser("check", help="Evaluate policy; return allow/warn/deny")
    pcheck.add_argument("bundle_dir", type=Path, nargs="?", default=None, help="Bundle directory")
    pcheck.add_argument(
        "--strictness",
        choices=("permissive", "standard", "strict"),
        default="standard",
    )
    pcheck.add_argument("--action", default="run", help="Action: run, export, share, purge, delete")
    pcheck.add_argument("--legal-hold", action="store_true")
    pcheck.add_argument("--retention-raw-ttl-hours", type=float, default=None)
    pcheck.add_argument("--retention-derived-ttl-days", type=float, default=None)
    pcheck.add_argument("--data-classification", type=str, default=None)
    pcheck.add_argument("--pii-present", type=str, default=None)
    pcheck.add_argument("--consent-basis", type=str, default=None)
    pcheck.add_argument("--purpose-of-processing", type=str, default=None)
    pcheck.set_defaults(_run=_cmd_policy_check)
    pexplain = policy_sub.add_parser("explain", help="Print decision reasoning and triggered rules")
    pexplain.add_argument("bundle_dir", type=Path, nargs="?", default=None)
    pexplain.add_argument(
        "--strictness",
        choices=("permissive", "standard", "strict"),
        default="standard",
    )
    pexplain.add_argument("--action", default="run")
    pexplain.add_argument("--legal-hold", action="store_true")
    pexplain.add_argument("--retention-raw-ttl-hours", type=float, default=None)
    pexplain.add_argument("--retention-derived-ttl-days", type=float, default=None)
    pexplain.add_argument("--data-classification", type=str, default=None)
    pexplain.add_argument("--pii-present", type=str, default=None)
    pexplain.add_argument("--consent-basis", type=str, default=None)
    pexplain.add_argument("--purpose-of-processing", type=str, default=None)
    pexplain.set_defaults(_run=_cmd_policy_explain)

    # hashen retention status
    retention_p = sub.add_parser("retention", help="Retention subcommands")
    retention_sub = retention_p.add_subparsers(dest="retention_cmd", required=True)
    rstatus = retention_sub.add_parser("status", help="Show lifecycle state and retention window")
    rstatus.add_argument("bundle_dir", type=Path, nargs="?", help="Bundle directory")
    rstatus.add_argument("--path", type=Path, default=None, help="Alias for bundle_dir")
    rstatus.add_argument("--raw-ttl-hours", type=float, default=24)
    rstatus.add_argument("--derived-ttl-days", type=float, default=365)
    rstatus.add_argument("--legal-hold", action="store_true")
    rstatus.set_defaults(_run=_cmd_retention_status)

    # hashen exec validate/run/explain-policy
    exec_p = sub.add_parser("exec", help="Restricted execution subcommands (best-effort)")
    exec_sub = exec_p.add_subparsers(dest="exec_cmd", required=True)
    ev = exec_sub.add_parser("validate", help="Validate a script against restricted policy")
    ev.add_argument("script_path", type=Path, help="Path to Python script")
    ev.add_argument(
        "--mode",
        choices=("disabled", "restricted_local", "isolated_subprocess", "container_unsupported"),
        default="isolated_subprocess",
    )
    ev.add_argument("--allow-import", action="append", default=[], help="Additional allowed import")
    ev.add_argument("--allow-network", action="store_true")
    ev.add_argument("--allow-filesystem-write", action="store_true")
    ev.add_argument("--allow-subprocess-spawn", action="store_true")
    ev.add_argument("--max-runtime-seconds", type=float, default=None)
    ev.add_argument("--max-output-bytes", type=int, default=None)
    ev.set_defaults(_run=_cmd_exec_validate)

    er = exec_sub.add_parser("run", help="Run a script in restricted mode")
    er.add_argument("script_path", type=Path, help="Path to Python script")
    er.add_argument(
        "--mode",
        choices=("disabled", "restricted_local", "isolated_subprocess", "container_unsupported"),
        default="isolated_subprocess",
    )
    er.add_argument("--timeout-sec", type=float, default=5.0)
    er.add_argument("--strict-mode", action="store_true")
    er.add_argument("--allow-import", action="append", default=[], help="Additional allowed import")
    er.add_argument("--allow-network", action="store_true")
    er.add_argument("--allow-filesystem-write", action="store_true")
    er.add_argument("--allow-subprocess-spawn", action="store_true")
    er.add_argument("--max-runtime-seconds", type=float, default=None)
    er.add_argument("--max-output-bytes", type=int, default=None)
    er.set_defaults(_run=_cmd_exec_run)

    ep = exec_sub.add_parser("explain-policy", help="Explain default restricted execution policy")
    ep.set_defaults(_run=_cmd_exec_explain_policy)

    args = ap.parse_args()
    return args._run(ap, args)


if __name__ == "__main__":
    sys.exit(main())
