# Evidence

## CI Gate

File: `.github/workflows/ci.yml`

Relevant lines:

```text
51      - name: Ruff
52        run: python -m ruff check autodev financial-engine_v2/backend scripts
```

Blame:

```text
ad14f1761 ... 51)       - name: Ruff
ad14f1761 ... 52)         run: python -m ruff check autodev financial-engine_v2/backend scripts
```

## Local Validation Runbook

File: `docs/validation_baseline.md`

Relevant lines:

```text
5   GitHub Actions runs ruff + pytest ... see `.github/workflows/ci.yml`
15  python -m ruff check autodev financial-engine_v2/backend scripts
27  Ruff check on `autodev`, `financial-engine_v2/backend`, and `scripts`
47  `ruff` is pinned in `financial-engine_v2/backend/requirements.txt` ...
```

Blame:

```text
ceb8bb1c3 ... 15) python -m ruff check autodev financial-engine_v2/backend scripts
ceb8bb1c3 ... 47) - `ruff` is pinned in `financial-engine_v2/backend/requirements.txt` ...
```

## Dependency Evidence

Files:

- `requirements.txt`
- `financial-engine_v2/backend/requirements.txt`

Relevant lines:

```text
requirements.txt:1:-r financial-engine_v2/backend/requirements.txt
requirements.txt:2:-r financial-engine_v2/worker/requirements.txt
financial-engine_v2/backend/requirements.txt:34:ruff==0.15.6
```

Blame:

```text
7e9a61805 ... requirements.txt:1) -r financial-engine_v2/backend/requirements.txt
af7f8e578 ... financial-engine_v2/backend/requirements.txt:34) ruff==0.15.6
```

## Local Tool Availability

The current shell Python does not have Ruff:

```text
python3 -m ruff --version
/usr/bin/python3: No module named ruff
```

The repo venv does have the pinned Ruff binary:

```text
financial-engine_v2/.venv/bin/ruff --version
ruff 0.15.6
```

## Acceptance-Criteria Mapping

| #281 criterion | Current evidence | Status |
| --- | --- | --- |
| Documented command exists | `docs/validation_baseline.md:15` | Satisfied |
| CI or local scripts can run it without external services | `.github/workflows/ci.yml:51-52`; repo venv Ruff available | Satisfied for CI and existing repo venv |
| Generated/legacy paths excluded/configured | Command scopes `autodev`, `financial-engine_v2/backend`, and `scripts`; no broad repo lint | Satisfied enough for the stated Ruff gate |

## Caveat

No full Ruff check was run, and no type checker was added or run. The issue body
describes type/import checking as optional later work, so this does not block
closing the minimum Ruff-gate issue unless the owner wants #281 re-scoped.
