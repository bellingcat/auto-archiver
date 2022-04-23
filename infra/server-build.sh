#!/bin/sh

# Script to configure production server

# Create a clean VM
# Proxmox, shutdown VM, backup, restore

# connect to the VM
# ssh pfsense -p 30 

# git clone https://github.com/djhmateer/auto-archiver ;  sudo chmod +x ~/auto-archiver/infra/server-build.sh ; ./auto-archiver/infra/server-build.sh

# Use Filezilla to copy secrets - `.env` and `service-account.json` and `anon.session`

## Python
sudo apt update -y
sudo apt upgrade -y
sudo apt autoremove -y

sudo add-apt-repository ppa:deadsnakes/ppa -y

sudo apt update -y

# 3.9.12
sudo apt install python3.9 -y


export PATH=/home/dave/.local/bin:$PATH

sudo apt install python3-pip -y

# update pip to 22.0.4
pip install --upgrade pip

# We are calling pipenv from cron so need to install this way
# https://stackoverflow.com/questions/46391721/pipenv-command-not-found
# pip install --user pipenv
sudo -H pip install -U pipenv

cd auto-archiver

# get all the pip packages using pipenv
pipenv install

# FFMpeg
# 4.4.1
sudo add-apt-repository ppa:savoury1/ffmpeg4 -y
sudo apt update -y
sudo apt upgrade -y
sudo apt install ffmpeg -y

## Firefox
sudo apt install firefox -y

## Gecko driver
# check version numbers for new ones
cd ~
wget https://github.com/mozilla/geckodriver/releases/download/v0.30.0/geckodriver-v0.30.0-linux64.tar.gz
tar -xvzf geckodriver*
chmod +x geckodriver
sudo mv geckodriver /usr/local/bin/
rm geckodriver*

# got issue with telethon archiver
# Please enter your phone (or bot token):
# then failing after that (even aftrer manually giving access)

# RUN MANUALLY
# cd ~/auto-archiver
# pipenv run python auto_archive.py --sheet "Test Hashing"

## CRON RUN EVERY MINUTE

# so the cron job can execute the shell script (running as user dave)
sudo chmod +x ~/auto-archiver/infra/cron.sh

# to stop errors
# https://askubuntu.com/questions/1383506/deprecation-warnings-python3-8-packages
#/usr/local/lib/python3.8/dist-packages/pkg_resources/__init__.py:123: PkgResourcesDeprecationWarning: 0.23ubuntu1 is an invalid version and will not be supported in a future release      
sudo mv /usr/local/lib/python3.8/dist-packages/pkg_resources pkg_resources_back


# runs the script every minute
cat <<EOT >> run-auto-archive 
* * * * * dave /home/dave/auto-archiver/infra/cron.sh
EOT

sudo mv run-auto-archive /etc/cron.d

sudo chown root /etc/cron.d/run-auto-archive
sudo chmod 600 /etc/cron.d/run-auto-archive

# MONITORING
# syslog in /var/log/syslog
# cron output is in /home/dave/log.txt

# sudo service cron restart

