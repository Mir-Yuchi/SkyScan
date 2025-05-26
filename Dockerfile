FROM python:3.13-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml poetry.lock /app/

RUN pip install "poetry>=1.8.0" \
    && poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --only main --no-root

COPY . /app

ENV PORT=8000
EXPOSE 8000

CMD alembic upgrade head && \
    exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
