# Hashen Trust Layer

Enterprise-grade trust layer: tamper-evident seal (EPW), hash-chained audit log, secure sandbox runner, content-fingerprint cache, and compliance-by-design (retention, privacy tags, reports).

## Bootstrap

```bash
# Create virtualenv (recommended)
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/macOS

# Install in editable mode
pip install -e .
```

## Tests

```bash
pytest
```

With coverage and ruff:

```bash
pip install ruff
ruff check src tools tests
ruff format --check src tools tests
pytest -v
```

## End-to-end evidence bundle demo

1. **Run the evidence bundle tool** (ingest an artifact, run pipeline, produce bundle):

   ```bash
   python tools/run_evidence_bundle.py <path_to_artifact> <run_id> [--output-dir DIR]
   ```

   Example:

   ```bash
   echo "hello" > sample.bin
   python tools/run_evidence_bundle.py sample.bin demo-run-1 --output-dir bundle_demo
   ```

   This creates `bundle_demo/` with:
   - `artifact.bin` (copy of input)
   - `audit.jsonl` (hash-chained audit log)
   - `seal.json` (provenance seal with EPW hash)
   - `verify.json` (verification result: ok, audit_head_hash, seal_hash)

2. **Verify the bundle** (artifact + seal + audit chain):

   ```bash
   python tools/verify_bundle.py bundle_demo
   ```

   Output: `Verification OK`

3. **Tamper and re-verify** (must fail):

   ```bash
   echo "tampered" > bundle_demo/artifact.bin
   python tools/verify_bundle.py bundle_demo
   ```

   Output: `Seal verification FAILED: EPW_MISMATCH`

## Retention cleanup

```bash
python tools/retention_cleanup.py <directory> [--raw-ttl-hours 24] [--legal-hold]
```

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs on push/PR:

- pytest
- ruff (lint + format check)
- pip-audit (fail on high severity)
- CycloneDX SBOM → `sbom/bom.json`

## Docs

- `docs/SECURITY.md` – deterministic recomputation, fixed H2 range, seal + audit
- `docs/THREAT_MODEL.md` – threats and mitigations
- `docs/REASON_CODES.md` – verification failure reason codes
