FROM webrecorder/browsertrix-crawler:latest

ENV RUNNING_IN_DOCKER=1

WORKDIR /app

# TODO: use custom ffmpeg builds instead of apt-get install
RUN pip install --upgrade pip && \
	pip install pipenv && \
	add-apt-repository ppa:mozillateam/ppa && \
	apt-get update && \
	apt-get install -y gcc ffmpeg fonts-noto exiftool && \
	apt-get install -y --no-install-recommends firefox-esr && \
	ln -s /usr/bin/firefox-esr /usr/bin/firefox && \
	wget https://github.com/mozilla/geckodriver/releases/download/v0.33.0/geckodriver-v0.33.0-linux64.tar.gz && \
	tar -xvzf geckodriver* -C /usr/local/bin && \
	chmod +x /usr/local/bin/geckodriver && \
	rm geckodriver-v*


# TODO: avoid copying unnecessary files, including .git
COPY Pipfile* ./
# install from pipenv, with browsertrix-only requirements
RUN pipenv install && \
	pipenv install pywb uwsgi
	
# doing this at the end helps during development, builds are quick
COPY ./src/ . 

# TODO: figure out how to make volumes not be root, does it depend on host or dockerfile?
# RUN useradd --system --groups sudo --shell /bin/bash archiver && chown -R archiver:sudo .
# USER archiver


ENTRYPOINT ["pipenv", "run", "python3", "-m", "auto_archiver"]

# should be executed with 2 volumes (3 if local_storage is used)
# docker run --rm -v $PWD/secrets:/app/secrets -v $PWD/local_archive:/app/local_archive aa pipenv run python3 -m auto_archiver --config secrets/orchestration.yaml