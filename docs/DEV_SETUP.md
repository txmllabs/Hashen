# Developer setup

## Install and run tests

```bash
# Editable install with dev extras (pytest, ruff, pip-audit, cyclonedx-bom, pre-commit)
pip install -e ".[dev]"

# Run tests
pytest -q
```

## Pre-commit (format, lint, secret guard)

Install hooks so they run automatically before each commit:

```bash
pre-commit install
```

Run all hooks on the repo (e.g. after clone):

```bash
pre-commit run -a
```

Hooks include: **ruff** (lint), **ruff-format** (format), **trailing-whitespace**, **end-of-file-fixer**, **check-yaml**, **detect-private-key**, **check-added-large-files** (max 2MB).

## One-time setup summary

1. `pip install -e ".[dev]"`
2. `pre-commit install`
3. `pre-commit run -a` (optional; fix any issues)
4. `pytest -q`

## Windows: equivalent of `make quality`

On Windows (without Make), run the same steps in order:

```powershell
pytest -q
ruff check src tests; ruff format --check src tests
pip-audit --strict --desc
New-Item -ItemType Directory -Force sbom; cyclonedx-py environment --pyproject pyproject.toml --outfile sbom/bom.json --output-format JSON
[System.IO.File]::WriteAllBytes("sample.bin", [System.Text.Encoding]::UTF8.GetBytes("hashen-ci"))
python tools/run_evidence_bundle.py sample.bin ci-run --output-dir bundle_ci
python tools/verify_bundle.py bundle_ci
```

Or install Make (e.g. Chocolatey: `choco install make`) and run `make quality`. Note: RLIMIT_CPU/RLIMIT_AS are not enforced on Windows; sandbox memory-limit tests are skipped there.
