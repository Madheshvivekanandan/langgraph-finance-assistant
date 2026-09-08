# syntax=docker/dockerfile:1
# check=error=true
# Dev image: tag-pinned only (no digest) — rebuilt locally, not promoted anywhere.
FROM python:3.14-slim

RUN groupadd --gid 10001 app && \
    useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app

# Install runtime dependencies only (not the package itself) so this layer is
# cached until pyproject.toml changes; source arrives via COPY / bind mount.
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=pyproject.toml,target=/tmp/pyproject.toml \
    python -c "import subprocess, tomllib; \
deps = tomllib.load(open('/tmp/pyproject.toml', 'rb'))['project']['dependencies']; \
subprocess.run(['pip', 'install', *deps], check=True)"

COPY --chown=10001:10001 alembic.ini ./
COPY --chown=10001:10001 app/ ./app/

ENV PYTHONUNBUFFERED=1
USER 10001:10001
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health').read()"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
