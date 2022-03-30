# script to configure production server
# on proxmox hypervisor

# assume 16GB disk space
# 4 vcpu
# Ubuntu 20.04

git clone https://github.com/djhmateer/auto-archiver


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

pip install --user pipenv

cd auto-archiver

# get all the pip packages using pipenv
pipenv install


# FFMpeg
# 4.4.1
sudo add-apt-repository ppa:savoury1/ffmpeg4 -y
sudo apt update -y
sudo apt upgrade -y
# do I need to do this again as ffmeg installed already?
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

# get google secret: service_account.json
# use filezilla

# get env secrests: .env
# use filezilla

cd ~/auto-archiver
pipenv run python auto_archive.py --sheet "Test Hashing"
