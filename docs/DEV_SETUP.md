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
