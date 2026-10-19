# syntax=docker/dockerfile:1

# ---------- Stage 1: builder ----------
# Installs Python dependencies into an isolated virtualenv. Build tools and
# pip caches stay in this stage and never reach the final image.
FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

# Copy only the dependency manifest first. This layer is cached as long as
# requirements.txt does not change, so source edits do not reinstall packages.
COPY app/requirements.txt .

RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# ---------- Stage 2: runtime ----------
# Slim runtime with only the interpreter, the virtualenv and the app source.
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_VERSION=1.2.0

# Unprivileged user with no login shell and no home directory contents.
RUN groupadd --system app \
    && useradd --system --gid app --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app

# Dependencies from the builder stage, then the source code last, because the
# source changes most often and should invalidate as few layers as possible.
COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app app/ .

USER app

EXPOSE 8000

# Hits the real /healthz endpoint using the standard library, so the slim
# image does not need curl or wget.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import sys, urllib.request; \
        sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2).status == 200 else 1)"

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "app:app"]
