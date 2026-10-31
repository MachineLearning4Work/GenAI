FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    RUNS_DIR=/app/runs

WORKDIR /app

# Install the project and its declared runtime dependencies.
COPY pyproject.toml README.md /app/
COPY src/ /app/src/
RUN --mount=type=cache,target=/root/.cache/pip pip install --upgrade pip \
 && pip install . "pytest>=8.2,<9" "httpx>=0.28.1,<0.29"

COPY tests/ /app/tests/
COPY scripts/ /app/scripts/

RUN mkdir -p /app/runs

CMD ["uvicorn", "business_plan.api:app", "--host", "0.0.0.0", "--port", "8000"]
