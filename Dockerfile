FROM python:3.13-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.7 /uv /uvx /bin/

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential g++ make cmake python3-dev pkg-config libgomp1 curl ca-certificates gnupg && \
    rm -rf /var/lib/apt/lists/*

# Setup the app in workspace
WORKDIR /workspace

# Install node from upstream
RUN curl -sL https://deb.nodesource.com/setup_18.x | bash
RUN apt-get install -y nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install node package manager yarn
RUN npm install -g yarn

# Install frontend dependencies and build frontend
COPY frontend/package.json frontend/yarn.lock ./frontend/
RUN cd frontend && yarn install
COPY frontend ./frontend
RUN cd frontend && yarn build

# Install backend dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --locked

COPY wikidatasearch ./wikidatasearch

# Container start script
CMD [ "uv", "run", "uvicorn", "wikidatasearch:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "4" ]