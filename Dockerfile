FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY agents ./agents
RUN pip install --no-cache-dir .
ENV AGENTBASE_AGENTS_DIR=/app/agents \
    AGENTBASE_DATA_DIR=/data \
    AGENTBASE_WORKSPACE=/workspace
VOLUME ["/data", "/workspace"]
EXPOSE 8000
CMD ["uvicorn", "agentbase.server:app", "--host", "0.0.0.0", "--port", "8000"]