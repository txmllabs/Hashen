# Hashen one-command workflow (Unix)
.PHONY: test lint audit sbom evidence quality

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

quality: test lint audit sbom evidence
