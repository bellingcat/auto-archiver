From python:3.10

WORKDIR /usr/src/app

COPY . .


# TODO: use custom ffmpeg builds instead of apt-get install
RUN pip install --upgrade pip && \
	pip install pipenv && \
	apt-get update && \
	apt-get install -y gcc ffmpeg fonts-noto firefox-esr && \
	wget https://github.com/mozilla/geckodriver/releases/download/v0.32.0/geckodriver-v0.32.0-linux64.tar.gz && \
	tar -xvzf geckodriver* -C /usr/bin && \
	chmod +x /usr/bin/geckodriver && \
	rm geckodriver-v* && \
	export PATH=$PATH:/usr/bin/ && \
	pipenv install --python=3.10

CMD ["pipenv", "run", "python", "auto_archive.py"]