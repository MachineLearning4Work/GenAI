FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml /app/
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/* || true
RUN pip install --upgrade pip
# Install minimal runtime dependencies directly to keep the image simple and teaching-friendly
RUN pip install pydantic boto3 requests pytest fastapi uvicorn[standard]
COPY src/ /app/src/
WORKDIR /app/src
CMD ["python", "-m", "business_plan.main"]
