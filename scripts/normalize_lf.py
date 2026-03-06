#!/usr/bin/env python3
"""Write pyproject.toml and .github/workflows/ci.yml with LF only and update Git index to use those blobs."""
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

PYPROJECT = """[build-system]
requires = ["setuptools>=61", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "hashen"
version = "0.1.0"
description = "Trust and provenance verification layer: seal (EPW), audit chain, cache, restricted execution"
readme = "README.md"
requires-python = ">=3.9"
dependencies = []
license = { text = "Apache-2.0" }

[project.optional-dependencies]
dev = [
  "pytest>=8.0",
  "pytest-cov>=4.0",
  "ruff>=0.4",
  "pip-audit>=2.7",
  "cyclonedx-bom>=4.5",
  "pre-commit>=3.7",
]
signing = ["cryptography>=41.0"]

[project.scripts]
hashen-bundle = "hashen.cli.bundle:main"
hashen-verify = "hashen.cli.verify:main"
hashen-retention = "hashen.cli.retention:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-v"

[tool.ruff]
line-length = 100
target-version = "py39"

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]
ignore = ["UP045"]
per-file-ignores = { "examples/*.py" = ["E402"] }

[tool.ruff.format]
quote-style = "double"
""" + "\n"

CI_YML = """name: CI

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Secret scanning (gitleaks)
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: Install (single)
        run: python -m pip install -U pip && pip install -e ".[dev]"

      - name: Compile check
        run: python -m compileall -q src

      - name: Pip check
        run: pip check

      - name: Pytest
        run: pytest -q

      - name: Ruff check
        run: ruff check src tests

      - name: Ruff format check
        run: ruff format --check src tests

      - name: pip-audit
        run: pip-audit --strict --desc

      - name: CycloneDX SBOM
        run: |
          mkdir -p sbom
          cyclonedx-py environment --pyproject pyproject.toml --outfile sbom/bom.json --output-format JSON

      - name: Evidence-bundle smoke test
        run: |
          echo "hashen-ci" > sample.bin
          python tools/run_evidence_bundle.py sample.bin ci-run --output-dir bundle_ci
          python tools/verify_bundle.py bundle_ci

      - name: Upload SBOM
        uses: actions/upload-artifact@v4
        with:
          name: sbom
          path: sbom/
          retention-days: 7
""" + "\n"


def main() -> int:
    os.chdir(REPO_ROOT)
    for path, content in [
        ("pyproject.toml", PYPROJECT),
        (".github/workflows/ci.yml", CI_YML),
    ]:
        data = content.encode("utf-8")
        assert b"\r" not in data, f"{path}: content must not contain CR"
        path_obj = REPO_ROOT / path
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        path_obj.write_bytes(data)
        r = subprocess.run(
            ["git", "hash-object", "-w", "--stdin"],
            input=data,
            capture_output=True,
            cwd=REPO_ROOT,
        )
        r.check_returncode()
        blob_hash = r.stdout.decode().strip()
        subprocess.run(
            ["git", "update-index", "--cacheinfo", "100644", blob_hash, path],
            check=True,
            cwd=REPO_ROOT,
        )
        print(f"{path} -> blob {blob_hash} (LF only)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
