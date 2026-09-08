# Single image, single process. Phase 1 runs the API and the workers together.
#
# When stages are later split into separate services, this same image is used
# with a different command (`dv worker --stage investigate`). That is why the
# entrypoint dispatches rather than hardcoding one command.

FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Build dependencies for the document parsers (lxml, pymupdf).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libxml2-dev \
        libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies first, so a source change does not reinstall the world.
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir ".[ingest]"

COPY config/ ./config/
COPY prompts/ ./prompts/
COPY migrations/ ./migrations/
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# SQLite lives here; mount a volume over it so runs survive a restart.
RUN mkdir -p /app/data
VOLUME ["/app/data"]

# Do not run as root.
RUN useradd --create-home --uid 10001 dv && chown -R dv:dv /app
USER dv

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["serve"]
