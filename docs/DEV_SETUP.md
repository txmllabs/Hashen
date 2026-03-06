# Developer setup

## 1. Environment and install

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate

pip install -e ".[dev]"
```

Dev extras include: pytest, pytest-cov, ruff, pip-audit, cyclonedx-bom, pre-commit.

## 2. Run tests

```bash
pytest -q
# Or: make test
```

## 3. Linting

```bash
ruff check src tests
ruff format --check src tests
# Or: make lint
```

To auto-fix and format: `ruff check src tests --fix` and `ruff format src tests`.

## 4. Generate an evidence bundle and verify

```bash
# Create a small dummy artifact, run pipeline, write bundle, then verify
echo -n "hashen-ci" > sample.bin
hashen-bundle sample.bin demo-run --output-dir bundle_demo
hashen-verify bundle_demo
# Or (tools): python tools/run_evidence_bundle.py sample.bin demo-run --output-dir bundle_demo
#             python tools/verify_bundle.py bundle_demo
# Or: make verify-demo   (Unix; same as make evidence)
```

Exit code of `hashen-verify` is 0 on success, non-zero on failure.

## 5. SBOM and audit

```bash
make sbom        # CycloneDX SBOM -> sbom/bom.json
make audit       # pip-audit (strict)
# Or: make quality   # test + lint + audit + sbom + verify-demo
```

## 6. Pre-commit (format, lint, secret guard)

Install hooks so they run automatically before each commit:

```bash
pre-commit install
pre-commit run -a   # run once on whole repo after clone
```

Hooks: ruff (lint), ruff-format, trailing-whitespace, end-of-file-fixer, check-yaml, detect-private-key, check-added-large-files (max 2MB).

## Windows

Without Make, run the same steps manually. See [MAKEFILE_WINDOWS.md](MAKEFILE_WINDOWS.md) for PowerShell equivalents of `make test`, `make lint`, `make sbom`, `make verify-demo`, `make quality`. RLIMIT_CPU/RLIMIT_AS are not enforced on Windows; sandbox memory-limit tests are skipped there.
