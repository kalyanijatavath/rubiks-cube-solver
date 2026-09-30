FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 RUBIK_CACHE_DIR=/app/.cache
WORKDIR /app

# kociemba is a C extension: build tools are needed at install time only
COPY requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && pip install -r requirements.txt \
    && apt-get purge -y build-essential && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

COPY rubik_tutor ./rubik_tutor
COPY data ./data

# Pre-build the cross lookup table so the first request is fast
RUN python -c "from rubik_tutor.beginner_solver import cross_table; print(len(cross_table()), 'cross states')" \
    && useradd -m app && chown -R app /app
USER app

EXPOSE 7860
# One worker keeps memory low (the cross table is ~100 MB); threads handle concurrency.
CMD gunicorn "rubik_tutor.server:create_app()" --bind 0.0.0.0:${PORT:-7860} --workers 1 --threads 4 --timeout 60
