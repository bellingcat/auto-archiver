FROM webrecorder/browsertrix-crawler:1.12.4 AS base

ENV RUNNING_IN_DOCKER=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    PATH="/root/.local/bin:$PATH"


ARG TARGETARCH

# Installing system dependencies
RUN	apt-get update && \
    apt-get install -y --no-install-recommends gcc ffmpeg fonts-noto exiftool python3-tk curl unzip 

# Poetry and runtime
FROM base AS runtime

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1


# Create a virtual environment for poetry and install it
RUN python3 -m venv /poetry-venv && \
    /poetry-venv/bin/python -m pip install --upgrade pip && \
    /poetry-venv/bin/python -m pip install "poetry>=2.0.0,<3.0.0"

# Add Deno for solving YT JS challenges
RUN curl -fsSL https://deno.land/install.sh | DENO_INSTALL=/usr sh

WORKDIR /app


COPY pyproject.toml poetry.lock README.md ./
# Copy dependency files and install dependencies (excluding the package itself)
RUN /poetry-venv/bin/poetry install --only main --no-root --no-cache


# Copy code: This is needed for poetry to install the package itself,
# but the environment should be cached from the previous step if toml and lock files haven't changed
COPY ./src/ .
RUN /poetry-venv/bin/poetry install --only main --no-cache


# Run as non-root user to avoid permission issues with mounted volumes (see #342)
# The base image already has an 'ubuntu' user at UID/GID 1000.
# Ensure directories that need write access at runtime are writable.
RUN chown 1000:1000 /app && \
    chown -R 1000:1000 /app/.venv/lib/python3.12/site-packages/seleniumbase/drivers/ && \
    mkdir -p /app/local_archive /app/secrets /tmp/archive && \
    chown -R 1000:1000 /app/local_archive /app/secrets /tmp/archive

# Update PATH to include virtual environment binaries
# Allowing entry point to run the application directly with Python
ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

USER 1000

ENTRYPOINT ["python3", "-m", "auto_archiver"]

# should be executed with 2 volumes (3 if local_storage is used)
# docker run --rm -v $PWD/secrets:/app/secrets -v $PWD/local_archive:/app/local_archive aa pipenv run python3 -m auto_archiver --config secrets/orchestration.yaml

