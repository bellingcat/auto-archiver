FROM webrecorder/browsertrix-crawler:1.0.4 AS base

RUN add-apt-repository ppa:mozillateam/ppa && \
	apt-get update && \
	apt-get install -y --no-install-recommends gcc ffmpeg fonts-noto exiftool && \
	apt-get install -y --no-install-recommends firefox-esr && \
	ln -s /usr/bin/firefox-esr /usr/bin/firefox && \
	wget https://github.com/mozilla/geckodriver/releases/download/v0.33.0/geckodriver-v0.33.0-linux64.tar.gz && \
	tar -xvzf geckodriver* -C /usr/local/bin && \
	chmod +x /usr/local/bin/geckodriver && \
	rm geckodriver-v* && \
    rm -rf /var/lib/apt/lists/*

FROM base AS pipenv

ENV RUNNING_IN_DOCKER=1
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONFAULTHANDLER=1

WORKDIR /

RUN pip install pipenv
COPY Pipfile* ./
COPY Pipfile.lock .
# install from pipenv, with browsertrix-only requirements
RUN PIPENV_VENV_IN_PROJECT=1 pipenv install --deploy

FROM base AS runtime

WORKDIR /app

# Copy virtual env built in pipenv stage
COPY --from=pipenv /.venv /.venv
ENV PATH="/.venv/bin:$PATH"

# doing this at the end helps during development, builds are quick
COPY ./src/ .

ENTRYPOINT ["python3", "-m", "auto_archiver"]
CMD ["--config", "secrets/orchestration.yaml"]
# should be executed with 2 volumes (3 if local_storage is used)
# docker run --rm -v $PWD/secrets:/app/secrets -v $PWD/local_archive:/app/local_archive aa pipenv run python3 -m auto_archiver --config secrets/orchestration.yaml
