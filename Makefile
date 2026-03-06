# Hashen one-command workflow
.PHONY: test lint audit sbom quality

test:
	pytest -q

lint:
	ruff check src tests && ruff format --check src tests

audit:
	pip-audit --strict --desc

sbom:
	mkdir -p sbom
	cyclonedx-py environment --pyproject pyproject.toml --outfile sbom/bom.json --output-format JSON

quality: test lint audit sbom
