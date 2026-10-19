# CI pipeline explained

Workflow file: [`.github/workflows/ci.yml`](.github/workflows/ci.yml).
It runs in the public mirror repository
[Sul1k/devops-week5-ci](https://github.com/Sul1k/devops-week5-ci), which holds
exactly the files in this folder at its root. GitHub only executes workflow
files that live in `.github/workflows/` at the root of a repository, so a copy
inside this homework folder is documentation, while the copy in the mirror is
the one that actually runs.

## CI, CD and CD

| Term | What happens automatically | What stays manual |
| --- | --- | --- |
| Continuous integration | Every change is merged often and verified by lint, tests and a build | Releasing |
| Continuous delivery | Everything above plus packaging a release that is ready to ship | Pressing the deploy button |
| Continuous deployment | Everything above plus deploying to production | Nothing |

This homework implements continuous integration. The build job produces an
image and its digest, which is the hand-off point for delivery in Week 6.

## Triggers

```yaml
on:
  push:
  pull_request:
  workflow_dispatch:
```

| Trigger | When it fires | Why it is there |
| --- | --- | --- |
| `push` | Any commit pushed to any branch | Fast feedback for the author |
| `pull_request` | A PR is opened or updated | Checks the merge result before review |
| `workflow_dispatch` | The **Run workflow** button in the Actions tab | Re-run on demand, for example to show a warm cache |

The token is limited to `permissions: contents: read`. The pipeline needs no
secrets and no cloud credentials, so none are configured.

## Jobs

```
 lint ──────────┐
                ├──▶ build
 test (3.12) ───┤
 test (3.13) ───┘
```

`lint` and the two `test` jobs start at the same time on separate runners.
`build` declares `needs: [lint, test]`, so it only starts after all three
succeeded. One red job anywhere means no image is built.

### lint

Installs the dev requirements and runs `ruff check` (unused imports, undefined
names, import order, common bug patterns) and `ruff format --check` (code
style). Ruff exits non-zero on the first finding, which fails the job.
`--output-format=github` turns findings into annotations on the changed lines.

### test

Runs `pytest` against the 9 tests in `tests/test_app.py`:

- `/healthz` answers 200 with `{"status": "ok"}`
- `/` answers JSON that carries the app version and a greeting
- `/hello/<name>` puts the name into the greeting
- an unknown route answers 404
- the pure `greeting()` function, parametrised over five inputs

`pytest` exits with code 1 when any test fails. GitHub treats a non-zero exit
as a failed step, the step fails the job, and the job fails the workflow. No
`continue-on-error` is set anywhere, so there is no way for a red test to
produce a green run.

The results are written to `test-results/junit-py<version>.xml` and uploaded
as an artifact with `if: always()`, so the report is available for a failing
run too, which is exactly when you want to read it.

### build

Builds the multi-stage `Dockerfile` from Week 3 with Buildx, loads it into the
runner's Docker daemon, starts a container and polls `/healthz` for up to 30
seconds. If the container never becomes healthy the job prints its logs and
fails. On success it writes `image-digest.txt` (tag, image id, content digest,
commit, timestamp) and uploads it as the second artifact.

## Matrix

```yaml
strategy:
  fail-fast: true
  matrix:
    python-version: ["3.12", "3.13"]
```

One job definition, two parallel runs. The image ships Python 3.12, and 3.13
proves the app is ready for the next base image bump. `fail-fast: true`
cancels the sibling run as soon as one version fails, which saves runner time
and surfaces the failure sooner.

## Caching

Two caches are used.

**pip cache** in `lint` and `test`, through `actions/setup-python` with
`cache: pip`. The cache key is a hash of `requirements-dev.txt` and
`app/requirements.txt`. While those files do not change, the wheels for Flask,
gunicorn, pytest and ruff are restored from the cache instead of being
downloaded from PyPI again. The install step drops from roughly 10 seconds to
roughly 2 seconds, and more importantly it no longer depends on PyPI being
reachable.

**Docker layer cache** in `build`, through `cache-from: type=gha` and
`cache-to: type=gha,mode=max`. Unchanged layers, above all the base image and
the `pip install` layer of the builder stage, are pulled from the GitHub
Actions cache. A rebuild after a source-only change reuses every layer up to
`COPY app/ .`.

Caches are keyed per branch and fall back to the default branch, so a pull
request benefits from the cache that `main` already populated.

## Artifacts

| Artifact | Produced by | Contents |
| --- | --- | --- |
| `test-results-py3.12`, `test-results-py3.13` | test | JUnit XML report per Python version |
| `image-digest` | build | Image tag, image id, digest, commit, build time |

Artifacts are kept for 14 days and can be downloaded from the run summary page.

## Pinned versions

Every action is pinned to a major version tag: `actions/checkout@v4`,
`actions/setup-python@v5`, `actions/upload-artifact@v4`,
`docker/setup-buildx-action@v3`, `docker/build-push-action@v6`. The runner is
pinned to `ubuntu-24.04` rather than `ubuntu-latest`, so a runner image
upgrade cannot change the pipeline behind our back. Python packages are pinned
with `==` in the requirements files.

## Proving fail-fast

The branch `demo/failing-test` in the mirror repository changes one expected
value in `test_healthz_returns_ok`. The resulting run is red: both matrix
jobs fail, `build` is skipped, and the JUnit artifact shows the failing
assertion. The link to that run is in `README.md`.
