# DevOps homework, week 5: CI pipeline with GitHub Actions

[![CI](https://github.com/Sul1k/devops-week5-ci/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Sul1k/devops-week5-ci/actions/workflows/ci.yml?query=branch%3Amain)

Student: Sul1k. Class date 13-10-2026.

The Week 3 Flask app now has unit tests and a GitHub Actions workflow with
separate `lint`, `test` and `build` jobs, pip and Docker layer caching, a
Python version matrix, two uploaded artifacts and pinned action versions.

- Green run on `main`: <https://github.com/Sul1k/devops-week5-ci/actions/runs/39282131075> (push to `main`, all four jobs green)
- Red run with a broken test: <https://github.com/Sul1k/devops-week5-ci/actions/runs/39283509256> (branch `demo/failing-test`, workflow failed, build skipped)
- Workflow runs live here: <https://github.com/Sul1k/devops-week5-ci/actions>

## Where the workflow runs

GitHub executes workflow files only from `.github/workflows/` at the root of a
repository. This folder sits several levels deep in the course repository, so
the copy of `ci.yml` here can never be triggered. The public repository
[Sul1k/devops-week5-ci](https://github.com/Sul1k/devops-week5-ci) contains
exactly the files in this folder at its root. Every push to it, every pull
request against it and the manual **Run workflow** button start the pipeline,
and the badge above reflects the latest run on its `main` branch.

## Pipeline at a glance

```
push / pull_request / workflow_dispatch
            │
            ├── lint   ruff check + ruff format --check      (Python 3.12)
            ├── test   pytest, 9 tests, JUnit artifact       (Python 3.12)
            ├── test   pytest, 9 tests, JUnit artifact       (Python 3.13)
            │            ▲ matrix, fail-fast
            └── build  needs lint + test
                       docker buildx (layer cache) → run → curl /healthz
                       → image-digest artifact
```

A detailed walkthrough of every job, the triggers, the matrix, the caches and
the artifacts is in [CI.md](CI.md).

## Files

| Path | Purpose |
| --- | --- |
| `.github/workflows/ci.yml` | The workflow |
| `app/app.py` | Flask app: `/`, `/hello/<name>`, `/healthz` |
| `app/requirements.txt` | Runtime dependencies, pinned |
| `requirements-dev.txt` | Runtime plus `pytest` and `ruff`, pinned |
| `tests/test_app.py` | 9 unit tests using the Flask test client |
| `pytest.ini` | Test discovery and `pythonpath = app` |
| `ruff.toml` | Lint rules and line length |
| `Dockerfile` | Multi-stage image from Week 3, non-root user, health check |
| `.dockerignore` | Keeps tests, CI files and caches out of the image |
| `CI.md` | Explanation of the pipeline |

## Run the checks locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
ruff check . && ruff format --check .
pytest
docker build -t devops/week5-app:local .
docker run --rm -p 8000:8000 devops/week5-app:local
curl -s localhost:8000/healthz
```

Local result before the first push:

```
$ ruff check . && ruff format --check .
All checks passed!
2 files already formatted
$ pytest -q
.........                                                                [100%]
9 passed in 0.55s
```

## The tests

| Test | What it proves |
| --- | --- |
| `test_healthz_returns_ok` | `/healthz` answers 200 and `{"status": "ok"}`, the contract the Docker HEALTHCHECK relies on |
| `test_index_returns_json_with_version` | `/` returns JSON carrying the configured version and the greeting |
| `test_hello_route_uses_the_name` | `/hello/<name>` puts the URL parameter into the greeting |
| `test_unknown_route_is_404` | Flask's 404 handling is intact |
| `test_greeting` (5 cases) | The pure `greeting()` function trims whitespace and falls back to the default text |

## Proof that a failing test fails the workflow

The branch `demo/failing-test` changes the expected `/healthz` body from
`ok` to `healthy`. Nothing else differs. the run
<https://github.com/Sul1k/devops-week5-ci/actions/runs/39283509256> is red.

| Job | Result | Why |
| --- | --- | --- |
| Lint (ruff) | success | the broken line is still valid Python |
| Test (Python 3.12) | failure | `1 failed, 8 passed`, pytest exit code 1 |
| Test (Python 3.13) | cancelled | `fail-fast: true` stopped the sibling matrix job |
| Build image | skipped | `needs: [lint, test]` was not satisfied |

The JUnit artifacts were still uploaded because the upload step has
`if: always()`. The log shows the exact assertion:

```
>       assert response.get_json() == {"status": "healthy"}
E       AssertionError: assert {'status': 'ok'} == {'status': 'healthy'}
FAILED tests/test_app.py::test_healthz_returns_ok
========================= 1 failed, 8 passed in 0.29s =========================
```

## Caching in practice

Two runs on the same commit of `main`, the first after the repository was
created (empty cache) and the second started with the **Run workflow** button
(warm cache). Run links:
<https://github.com/Sul1k/devops-week5-ci/actions/runs/39282131075> and
<https://github.com/Sul1k/devops-week5-ci/actions/runs/39285529394>.

| Step | First run (cache miss) | Manual run (cache hit) |
| --- | --- | --- |
| Set up Python, pip cache | `Cache saved with the key: setup-python-Linux-x64-24.04-Ubuntu-python-3.12.15-pip-...` | `Cache hit`, `Cache restored from key: ...` |
| Install dev dependencies | wheels downloaded from PyPI | every package logged as `Using cached ...whl` |
| Build the image | 25 s, all layers built | 6 s, base image and `pip install` layer imported from the GitHub Actions cache |

The pip install for this small app is quick either way, about three seconds,
because the dependency set is tiny. The visible win is the Docker build, which
drops from 25 to 6 seconds, and the fact that neither step depends on PyPI or
Docker Hub being fast that day. `gh cache list` shows two pip caches of about
13 MB (one per Python version) and the BuildKit layer blobs.

## Requirements checklist

| Requirement | Where |
| --- | --- |
| Separate `lint`, `test`, `build` jobs | three jobs in `ci.yml`, `build` has `needs: [lint, test]` |
| Dependency caching | `actions/setup-python` with `cache: pip`; Buildx `cache-from/cache-to: type=gha` |
| Matrix across two language versions | `test` matrix `python-version: ["3.12", "3.13"]` |
| Artifact upload | `test-results-py3.12`, `test-results-py3.13`, `image-digest` |
| Fail fast | `pytest` non-zero exit fails the job; `fail-fast: true` on the matrix; red run linked above |
| Pinned action versions | `checkout@v4`, `setup-python@v5`, `upload-artifact@v4`, `setup-buildx-action@v3`, `build-push-action@v6`, runner `ubuntu-24.04` |
| At least three real unit tests | 9 tests in `tests/test_app.py` |
| No long-lived credentials | `permissions: contents: read`, no secrets referenced |
| No committed runs, caches or build output | `.gitignore` covers `test-results/`, `.pytest_cache/`, `.ruff_cache/`, `__pycache__/` |
