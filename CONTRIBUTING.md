# Contributing to Hashen

Thank you for your interest in contributing. Please follow these guidelines.

## Run tests and lint

```bash
pip install -e ".[dev]"
pytest -q
ruff check src tests
ruff format --check src tests
```

See [docs/DEV_SETUP.md](docs/DEV_SETUP.md) for pre-commit setup (format/lint/secret guard before each commit).

## Evidence bundle (dummy input only)

**Use only dummy or synthetic input** when creating evidence bundles for demos or tests. Never use real customer or production data in a public repo.

```bash
# Example: create a small dummy artifact
printf 'hashen-ci' > sample.bin
python tools/run_evidence_bundle.py sample.bin demo-run --output-dir bundle_demo
python tools/verify_bundle.py bundle_demo
```

Bundles (`bundle_*/`, `evidence/`) are gitignored. Do not commit them if they contain anything sensitive.

## Pull request checklist

Before submitting a PR, ensure:

- [ ] Tests pass: `pytest -q`
- [ ] Lint passes: `ruff check src tests && ruff format --check src tests`
- [ ] No secrets or keys in the diff (pre-commit `detect-private-key` helps)
- [ ] SBOM is generated in CI (`cyclonedx-py` step); no need to commit `sbom/` (it’s an artifact)

## Security and disclosure

Do not commit `.env`, API keys, tokens, or signing keys. See [SECURITY.md](SECURITY.md) for vulnerability reporting and [docs/DISCLOSURE_POLICY.md](docs/DISCLOSURE_POLICY.md) for prohibited uploads.
