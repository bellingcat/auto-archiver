# Installation

```{toctree}
:maxdepth: 1

upgrading.md
```

There are 3 main ways to use the auto-archiver. We recommend the 'docker' method for most uses. This installs all the requirements in one command.

1. Easiest (recommended): [via docker](#installing-with-docker)
2. Local Install: [using pip](#installing-locally-with-pip)
3. Developer Install: [see the developer guidelines](../development/developer_guidelines)

## 1. Installing with Docker

[![dockeri.co](https://dockerico.blankenship.io/image/bellingcat/auto-archiver)](https://hub.docker.com/r/bellingcat/auto-archiver)

Docker works like a virtual machine running inside your computer, making installation simple. You'll need to first set up Docker, and then download the Auto Archiver 'image':


**a) Download and install docker**

Go to the [Docker website](https://docs.docker.com/get-docker/) and download right version for your operating system. 

**b) Pull the Auto Archiver docker image**

Open your command line terminal, and copy-paste / type:

```bash
docker pull bellingcat/auto-archiver
```

This will download the docker image, which may take a while.

That's it, all done! You're now ready to set up [your configuration file](configurations.md). Or, if you want to use the recommended defaults, then you can [run Auto Archiver immediately](setup.md#running-a-docker-install).

------------

## 2. Installing Locally with Pip

1. Make sure you have python 3.10 or higher installed
2. Install the package with your preferred package manager: `pip/pipenv/conda install auto-archiver` or `poetry add auto-archiver`
3. Test it's installed with `auto-archiver --help`
4. Install other local dependency requirements (for example `ffmpeg`, `firefox`)

After this, you're ready to set up your [your configuration file](configurations.md), or if you want to use the recommended defaults, then you can [run Auto Archiver immediately](setup.md#running-a-local-install).

### Installing Local Requirements

If using the local installation method, you will also need to install the following dependencies locally:

1.[ffmpeg](https://www.ffmpeg.org/) - for handling of downloaded videos
2. [firefox](https://www.mozilla.org/en-US/firefox/new/) and [geckodriver](https://github.com/mozilla/geckodriver/releases) on a path folder like `/usr/local/bin` - for taking webpage screenshots with the screenshot enricher
3. (optional) [fonts-noto](https://fonts.google.com/noto) to deal with multiple unicode characters during selenium/geckodriver's screenshots: `sudo apt install fonts-noto -y`.
4. [Browsertrix Crawler docker image](https://hub.docker.com/r/webrecorder/browsertrix-crawler) for the WACZ enricher/archiver



## Developer Install

[See the developer guidelines](../development/developer_guidelines)