# Makefile targets on Windows

On Windows (without GNU Make), use these equivalents:

| Make target | Windows (PowerShell) |
|-------------|----------------------|
| `make test` | `pytest -q` |
| `make lint` | `ruff check src tests; ruff format --check src tests` |
| `make audit` | `pip-audit --strict --desc` |
| `make sbom` | `New-Item -ItemType Directory -Force sbom; cyclonedx-py environment --pyproject pyproject.toml --outfile sbom/bom.json --output-format JSON` |
| `make evidence` | `[System.IO.File]::WriteAllBytes("sample.bin", [System.Text.Encoding]::UTF8.GetBytes("hashen-ci")); python tools/run_evidence_bundle.py sample.bin ci-run --output-dir bundle_ci; python tools/verify_bundle.py bundle_ci` |
| `make quality` | Run test, lint, audit, sbom, evidence in sequence. |

Or install Make (e.g. via Chocolatey: `choco install make`) and run `make quality` as on Unix.

**Note:** Resource limits (RLIMIT_CPU, RLIMIT_AS) are not enforced on Windows; sandbox tests that rely on them are skipped.
