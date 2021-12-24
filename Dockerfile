FROM python:3.9.3-slim as base

ENV PYTHONUNBUFFERED=1

# Build stage - build server as wheel
FROM base as builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.1.11

RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    git \
    libpq-dev \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

RUN pip install "poetry==$POETRY_VERSION"
RUN python -m venv /venv

COPY /app /app
COPY pyproject.toml /
COPY poetry.lock /

RUN mkdir -p -m 0600 ~/.ssh && ssh-keyscan github.com >> ~/.ssh/known_hosts
RUN --mount=type=ssh poetry build && /venv/bin/pip install dist/*.whl

# Run stage - copy venv and run
FROM base as final

COPY --from=builder /venv /venv
ENV PATH="/venv/bin:$PATH"
RUN apt-get update && apt-get install -y libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY /alembic /alembic
COPY alembic.ini /
COPY migrate.py /

# Reasoning for options here:
# https://cloud.google.com/run/docs/quickstarts/build-and-deploy/python#containerizing
CMD exec gunicorn \
    --bind :$PORT \
    --workers 1 \
    --timeout 0 \
    -k uvicorn.workers.UvicornWorker \
    --access-logfile - \
    app.main:app