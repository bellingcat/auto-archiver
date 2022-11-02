From python:3.10

WORKDIR /app

COPY . .


# TODO: use custom ffmpeg builds instead of apt-get install
RUN pip install --upgrade pip && \
	pip install pipenv && \
	apt-get update && \
	apt-get install -y gcc ffmpeg fonts-noto firefox-esr

RUN wget https://github.com/mozilla/geckodriver/releases/download/v0.32.0/geckodriver-v0.32.0-linux64.tar.gz && \
	tar -xvzf geckodriver* -C /usr/local/bin && \
	chmod +x /usr/local/bin/geckodriver && \
	rm geckodriver-v* && \
	pipenv install --python=3.10

# CMD ["pipenv", "run", "python", "auto_archive.py"]
ENTRYPOINT ["pipenv", "run", "python", "auto_archive.py"]

# should be executed with 2 volumes
# docker run -v /var/run/docker.sock:/var/run/docker.sock -v $PWD/secrets:/app/ aa --help