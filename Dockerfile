FROM webrecorder/browsertrix-crawler:latest

ENV RUNNING_IN_DOCKER=1

WORKDIR /app

# TODO: use custom ffmpeg builds instead of apt-get install
RUN pip install --upgrade pip && \
	pip install pipenv && \
	apt-get update && \
	apt-get install -y gcc ffmpeg fonts-noto firefox && \
	wget https://github.com/mozilla/geckodriver/releases/download/v0.32.0/geckodriver-v0.32.0-linux64.tar.gz && \
	tar -xvzf geckodriver* -C /usr/local/bin && \
	chmod +x /usr/local/bin/geckodriver && \
	rm geckodriver-v* 


# TODO: avoid copying unnecessary files, including .git
COPY Pipfile* ./
RUN pipenv install

# doing this at the end helps during development, builds are quick
COPY ./src/ . 

# TODO: figure out how to make volumes not be root, does it depend on host or dockerfile?
# RUN useradd --system --groups sudo --shell /bin/bash archiver && chown -R archiver:sudo .
# USER archiver

ADD docker-entrypoint.sh /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]

CMD ["python3"]

# should be executed with 2 volumes (3 if local_storage)
# docker run -v /var/run/docker.sock:/var/run/docker.sock -v $PWD/secrets:/app/secrets  -v $PWD/local_archive:/app/local_archive aa --help