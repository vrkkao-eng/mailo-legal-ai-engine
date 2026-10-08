FROM python:3.12-slim@sha256:05cda9777409a9c3ffddd94a4c476b79f0769a0b4857f0c7ed9226b6800b0d6f AS builder

WORKDIR /build
COPY . .
RUN python -m pip wheel --no-cache-dir -c constraints.txt --wheel-dir /wheels ".[service]"

FROM python:3.12-slim@sha256:05cda9777409a9c3ffddd94a4c476b79f0769a0b4857f0c7ed9226b6800b0d6f

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MAILO_WORKFLOW_DB=/data/workflow.db

COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir --no-index --find-links=/wheels "mailo-legal-ai-engine[service]" \
    && groupadd --gid 10001 mailo \
    && useradd --uid 10001 --gid mailo --no-create-home --shell /usr/sbin/nologin mailo \
    && mkdir -p /app /data \
    && chown mailo:mailo /data

WORKDIR /app
USER 10001:10001

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/health', timeout=3).close()"]
CMD ["uvicorn", "mailo_cli.api:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
