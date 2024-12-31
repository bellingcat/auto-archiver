FROM webrecorder/browsertrix-crawler:1.0.4

ENV RUNNING_IN_DOCKER=1
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

RUN pip install --upgrade pip && \
    curl -sSL https://install.python-poetry.org | python3 - --version 1.8.3 && \
    poetry --version && \
    add-apt-repository ppa:mozillateam/ppa && \
    apt-get update && \
    apt-get install -y gcc ffmpeg fonts-noto exiftool && \
    apt-get install -y --no-install-recommends firefox-esr && \
    ln -s /usr/bin/firefox-esr /usr/bin/firefox && \
    wget https://github.com/mozilla/geckodriver/releases/download/v0.33.0/geckodriver-v0.33.0-linux64.tar.gz && \
    tar -xvzf geckodriver* -C /usr/local/bin && \
    chmod +x /usr/local/bin/geckodriver && \
    rm geckodriver-v*

COPY pyproject.toml poetry.lock ./

# Verify Poetry installation and install dependencies
RUN poetry install --no-root

# doing this at the end helps during development, builds are quick
COPY ./src/ .

ENTRYPOINT ["poetry", "run", "python3", "-m", "auto_archiver"]

# should be executed with 2 volumes (3 if local_storage is used)
# docker run --rm -v $PWD/secrets:/app/secrets -v $PWD/local_archive:/app/local_archive aa pipenv run python3 -m auto_archiver --config secrets/orchestration.yaml
