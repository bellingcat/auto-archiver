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
<!-- 2. [firefox](https://www.mozilla.org/en-US/firefox/new/) and [geckodriver](https://github.com/mozilla/geckodriver/releases) on a path folder like `/usr/local/bin` - for taking webpage screenshots with the screenshot enricher -->
3. (optional) [fonts-noto](https://fonts.google.com/noto) to deal with multiple unicode characters during selenium screenshots: `sudo apt install fonts-noto -y`.
4. [Browsertrix Crawler docker image](https://hub.docker.com/r/webrecorder/browsertrix-crawler) for the WACZ enricher/archiver

### Bash script for Ubuntu 24 Server install

This acts as a handy guide on all requirements. This is built and tested on the 29th of May 2025 on Ubuntu Server 24.04.2 LTS (which is the current latest LTS)

```bash
#!/bin/sh

# I usually run steps manually as logged in with the user: dave
# which the application runs under which makes debugging easier

cd ~
sudo apt update -y
sudo apt upgrade -y

# Clone only my latest branch
git clone -b v1-test --single-branch https://github.com/djhmateer/auto-archiver

mkdir ~/auto-archiver/secrets
sudo chown -R dave ~/auto-archiver

sudo apt update -y
sudo apt upgrade -y

## Python 3.12.3 comes with Ubuntu 24.04.2

# Poetry install 2.1.3 on 2nd June 25
curl -sSL https://install.python-poetry.org | python3 -

# had to restart here.. 
sudo reboot

# C++ compiler so pdqhash will install next
sudo apt install build-essential python3-dev -y

cd auto-archiver

poetry install

# FFMpeg
# 6.1.1-3ubuntu5 on 2nd June 25
sudo apt install ffmpeg -y

## Firefox
# 139.0+build2-0ubuntu0.24.04.1~mt1 on 2nd Jun 25
# 16th Jun - don't need anymore as using Chrome in antibot
# cd ~
# sudo add-apt-repository ppa:mozillateam/ppa -y

# echo '
# Package: *
# Pin: release o=LP-PPA-mozillateam
# Pin-Priority: 1001
# ' | sudo tee /etc/apt/preferences.d/mozilla-firefox

# echo 'Unattended-Upgrade::Allowed-Origins:: "LP-PPA-mozillateam:${distro_codename}";' | sudo tee /etc/apt/apt.conf.d/51unattended-upgrades-firefox

# sudo apt install firefox -y

wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb

# Chrome
cd ~
# got problems here - fixed below
# 137.0.7151.103 on 16th Jun 2025
sudo dpkg -i google-chrome-stable_current_amd64.deb

# fix dependencies on install above
sudo apt-get install -f

# had to click a lot on UI to get going.
# to test
# google-chrome

## Gecko driver
# check version numbers for new ones
# https://github.com/mozilla/geckodriver/releases/
wget https://github.com/mozilla/geckodriver/releases/download/v0.36.0/geckodriver-v0.36.0-linux64.tar.gz
tar -xvzf geckodriver*
chmod +x geckodriver
sudo mv geckodriver /usr/local/bin/
rm geckodriver*

# Fonts so selenium via firefox can render other languages eg Burmese
sudo apt install fonts-noto -y

# Docker
# Add Docker's official GPG key:
sudo apt-get update -y
sudo apt-get install ca-certificates curl -y
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update -y

sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y

# add dave user to docker group 
sudo usermod -aG docker $USER

# reboot otherwise can't pull images

# https://github.com/webrecorder/browsertrix-crawler
# https://hub.docker.com/r/webrecorder/browsertrix-crawler/tags
# 1.6.2 on 4th Jun 2025
docker pull webrecorder/browsertrix-crawler:latest

# exif
sudo apt install libimage-exiftool-perl -y


## CRON run every minute
# the cron job running as user dave will execute the shell script
# I have many scripts running from cron_11 upwards.
# patch in the correct number
sudo chmod +x ~/auto-archiver/scripts/cron_15.sh

# don't want service to run until a reboot otherwise problems with Gecko driver
sudo service cron stop

# runs the script every minute
# notice put in a # to disable so will have to manually start it.
cat <<EOT >> run-auto-archive
#*/1 * * * * dave /home/dave/auto-archiver/scripts/cron_15.sh
EOT

sudo mv run-auto-archive /etc/cron.d
sudo chown root /etc/cron.d/run-auto-archive
sudo chmod 600 /etc/cron.d/run-auto-archive

# Helper alias 'c' to open the above file
echo "alias c='sudo vim /etc/cron.d/run-auto-archive'" >> ~/.bashrc

# secrets folder copy
# I run dev from:
# \\wsl.localhost\Ubuntu-24.04\home\dave\code\auto-archiver\secrets\

# orchestration.yaml - for aa config
# service_account - for google spreadsheet
# anon.session - for telethon so don't have to type in phone number
# profile.tar.gz - for wacz to have a logged in profile for facebook, x.com and instagram to get data

# Youtube - POT Tokens
# https://github.com/Brainicism/bgutil-ytdlp-pot-provider
docker run --name bgutil-provider --restart unless-stopped -d -p 4416:4416 brainicism/bgutil-ytdlp-pot-provider


# test run
cd ~/auto-archiver

poetry run python src/auto_archiver --config secrets/orchestration-aa-demo-main.yaml
```



## Developer Install

[See the developer guidelines](../development/developer_guidelines)