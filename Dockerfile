FROM webrecorder/browsertrix-crawler:1.4.2 AS base

ENV RUNNING_IN_DOCKER=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    PATH="/root/.local/bin:$PATH"


ARG TARGETARCH

# Installing system dependencies
RUN add-apt-repository ppa:mozillateam/ppa && \
	apt-get update && \
    apt-get install -y --no-install-recommends gcc ffmpeg fonts-noto exiftool && \
	apt-get install -y --no-install-recommends firefox-esr && \
    ln -s /usr/bin/firefox-esr /usr/bin/firefox

ARG GECKODRIVER_VERSION=0.36.0

RUN if [ $(uname -m) = "aarch64" ]; then \
        GECKODRIVER_ARCH=linux-aarch64; \
    else \
        GECKODRIVER_ARCH=linux64; \
    fi && \
    wget https://github.com/mozilla/geckodriver/releases/download/v${GECKODRIVER_VERSION}/geckodriver-v${GECKODRIVER_VERSION}-${GECKODRIVER_ARCH}.tar.gz && \
    tar -xvzf geckodriver* -C /usr/local/bin && \
    chmod +x /usr/local/bin/geckodriver && \
    rm geckodriver-v* && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


# Poetry and runtime
FROM base AS runtime

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1


# Create a virtual environment for poetry and install it
RUN python3 -m venv /poetry-venv && \
    /poetry-venv/bin/python -m pip install --upgrade pip && \
    /poetry-venv/bin/python -m pip install "poetry>=2.0.0,<3.0.0"

WORKDIR /app


COPY pyproject.toml poetry.lock README.md ./
# Copy dependency files and install dependencies (excluding the package itself)
RUN /poetry-venv/bin/poetry install --only main --no-root --no-cache


# Copy code: This is needed for poetry to install the package itself,
# but the environment should be cached from the previous step if toml and lock files haven't changed
COPY ./src/ .
RUN /poetry-venv/bin/poetry install --only main --no-cache


# Update PATH to include virtual environment binaries
# Allowing entry point to run the application directly with Python
ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["python3", "-m", "auto_archiver"]

# should be executed with 2 volumes (3 if local_storage is used)
# docker run --rm -v $PWD/secrets:/app/secrets -v $PWD/local_archive:/app/local_archive aa pipenv run python3 -m auto_archiver --config secrets/orchestration.yaml

