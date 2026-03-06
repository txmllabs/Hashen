"""
Generate deterministic example fixtures from sample_artifact.bin.
Run from repo root: python examples/generate_fixtures.py
Writes expected_seal_structure.json, expected_manifest_structure.json, sample_verify_result.json.
No secrets; artifact is small and synthetic.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

EXAMPLES = Path(__file__).resolve().parent
REPO = EXAMPLES.parent
sys.path.insert(0, str(REPO / "src"))

from hashen.provenance.seal import create_seal
from hashen.utils.canonical_json import canonical_dumps

ARTIFACT_BYTES = b"hashen_example_artifact_v1\n"
CONFIG = {
    "h2_min": 0.0,
    "h2_max": 4.0,
    "h2_bins": 16,
    "h1_subset_size": 32,
}
AUDIT_HEAD = "0" * 64


def main() -> int:
    # Write deterministic artifact so it matches what we seal
    artifact_path = EXAMPLES / "sample_artifact.bin"
    artifact_path.write_bytes(ARTIFACT_BYTES)
    print("Wrote", artifact_path)

    full_record, epw_hash = create_seal(ARTIFACT_BYTES, CONFIG, AUDIT_HEAD)
    seal_path = EXAMPLES / "expected_seal_structure.json"
    with open(seal_path, "w", encoding="utf-8") as f:
        f.write(canonical_dumps(full_record))
    print("Wrote", seal_path)

    manifest_struct = {
        "schema_version": "hashen.manifest.v1",
        "files": {
            "artifact.bin": "<sha256 of artifact>",
            "audit.jsonl": "<sha256>",
            "seal.json": "<sha256>",
            "verify.json": "<sha256>",
        },
        "seal_hash": epw_hash,
        "audit_head_hash": AUDIT_HEAD,
    }
    manifest_path = EXAMPLES / "expected_manifest_structure.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_struct, f, indent=2, sort_keys=True)
    print("Wrote", manifest_path)

    verify_result = {
        "ok": True,
        "reason": None,
        "audit_head_hash": AUDIT_HEAD,
        "seal_hash": epw_hash,
    }
    verify_path = EXAMPLES / "sample_verify_result.json"
    with open(verify_path, "w", encoding="utf-8") as f:
        json.dump(verify_result, f, indent=2, sort_keys=True)
    print("Wrote", verify_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
