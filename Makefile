# Hashen one-command workflow (Unix). See docs/MAKEFILE_WINDOWS.md for PowerShell equivalents.
.PHONY: test lint audit sbom evidence verify-demo quality

test:
	pytest -q

lint:
	ruff check src tests && ruff format --check src tests

audit:
	pip-audit --strict --desc

sbom:
	mkdir -p sbom
	cyclonedx-py environment --pyproject pyproject.toml --outfile sbom/bom.json --output-format JSON

evidence:
	printf 'hashen-ci' > sample.bin
	python tools/run_evidence_bundle.py sample.bin ci-run --output-dir bundle_ci
	python tools/verify_bundle.py bundle_ci

# Alias for docs: run bundle then verify (same as evidence)
verify-demo: evidence

quality: test lint audit sbom evidence
