FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/agent-mem
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip install '.[mcp]' 'mcp>=1,<2' && useradd --create-home --uid 10001 agent && mkdir /workspace && chown agent:agent /workspace
USER agent
WORKDIR /workspace
CMD ["agent-mem", "serve", "--force-stdio"]
