# Release checklist

Use this before tagging a release (e.g. `v0.2.0`).

## 1. Update changelog

- Edit [CHANGELOG.md](../CHANGELOG.md): move items from `[Unreleased]` into a new `[X.Y.Z] - YYYY-MM-DD` section.
- Ensure all notable changes are listed; link to PRs or issues if applicable.

## 2. Run tests and quality

```bash
pip install -e ".[dev]"
pytest -q
ruff check src tests && ruff format --check src tests
pip-audit --strict --desc
```

Or: `make quality` (Unix).

## 3. Build artifacts

```bash
python -m pip install -U build
python -m build --outdir dist/
```

Verifies that the package builds (sdist and wheel) without errors.

## 4. Generate SHA256SUMS (optional, for distribution)

```bash
cd dist
# Unix/macOS:
sha256sum * > SHA256SUMS
# Windows PowerShell:
Get-ChildItem | ForEach-Object { Get-FileHash $_.FullName -Algorithm SHA256 } | Format-Table -AutoSize
```

The release workflow (`.github/workflows/release.yml`) does this automatically on tag push.

## 5. Verify demo bundle

```bash
echo -n "hashen-release" > sample.bin
hashen-bundle sample.bin release-check --output-dir bundle_release
hashen-verify bundle_release
# Expect exit 0 and "Verification OK"
```

## 6. Tag and push

```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin vX.Y.Z
```

Pushing a tag `v*` triggers the release workflow (build, SHA256SUMS, upload artifacts).

## Post-release

- Create a GitHub Release from the tag; attach `dist/*` and `dist/SHA256SUMS` if publishing outside PyPI.
- Announce in appropriate channels; update docs if release notes reference new features.
