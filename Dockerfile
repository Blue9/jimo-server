FROM python:3.12.1-slim as base

ENV PYTHONUNBUFFERED=1

# Build stage - build server as wheel
FROM base as builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.7.1

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

CMD exec gunicorn \
    --bind :$PORT \
    --workers 4 \
    -k uvicorn.workers.UvicornWorker \
    --access-logfile - \
    app.main:app
