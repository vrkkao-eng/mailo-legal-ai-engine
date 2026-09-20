FROM python:3.12-slim

WORKDIR /app
COPY . .
RUN python -m pip install --no-cache-dir ".[service]"

EXPOSE 8000
CMD ["uvicorn", "mailo_cli.api:app", "--host", "0.0.0.0", "--port", "8000"]
