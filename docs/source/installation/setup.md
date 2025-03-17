# Getting Started

```{toctree}
:hidden:

installation.md
configurations.md
config_editor.md
authentication.md
requirements.md
faq.md
config_cheatsheet.md
```

## Getting Started

To get started with Auto Archiver, there are 3 main steps you need to complete.

1. [Install Auto Archiver](installation.md)
2. [Setup up your configuration](configurations.md) (if you are ok with the default settings, you can skip this step)
3. Run the archiving process<a id="running"></a>

The way you run the Auto Archiver depends on how you installed it (docker install or local install)

### Running a Docker Install

If you installed Auto Archiver using docker, open up your terminal, and copy-paste / type the following command:

```bash
docker run --rm -v $PWD/secrets:/app/secrets -v $PWD/local_archive:/app/local_archive bellingcat/auto-archiver
 ```

breaking this command down:
   1. `docker run` tells docker to start a new container (an instance of the image)
   2. `--rm` makes sure this container is removed after execution (less garbage locally)
   3. `-v $PWD/secrets:/app/secrets` - your secrets folder with settings
      1. `-v` is a volume flag which means a folder that you have on your computer will be connected to a folder inside the docker container
      2. `$PWD/secrets` points to a `secrets/` folder in your current working directory (where your console points to), we use this folder as a best practice to hold all the secrets/tokens/passwords/... you use
      3. `/app/secrets` points to the path the docker container where this image can be found
   4.  `-v $PWD/local_archive:/app/local_archive` - (optional) if you use local_storage
       1.  `-v` same as above, this is a volume instruction
       2.  `$PWD/local_archive` is a folder `local_archive/` in case you want to archive locally and have the files accessible outside docker
       3.  `/app/local_archive` is a folder inside docker that you can reference in your orchestration.yml file 

### Example invocations

The invocations below will run the auto-archiver Docker image using a configuration file that you have specified

```bash
# Have auto-archiver run with the default settings, generating a settings file in ./secrets/orchestration.yaml
docker run --rm -v $PWD/secrets:/app/secrets -v $PWD/local_archive:/app/local_archive bellingcat/auto-archiver

# uses the same configuration, but with the `gsheet_feeder`, a header on row 2 and with some different column names
# Note this expects you to have followed the [Google Sheets setup](how_to/google_sheets.md) and added your service_account.json to the `secrets/` folder
# notice that columns is a dictionary so you need to pass it as JSON and it will override only the values provided
docker run --rm -v $PWD/secrets:/app/secrets -v $PWD/local_archive:/app/local_archive bellingcat/auto-archiver --feeders=gsheet_feeder --gsheet_feeder.sheet="use it on another sheets doc" --gsheet_feeder.header=2 --gsheet_feeder.columns='{"url": "link"}'
# Runs auto-archiver for the first time, but in 'full' mode, enabling all modules to get a full settings file
docker run --rm -v $PWD/secrets:/app/secrets -v $PWD/local_archive:/app/local_archive bellingcat/auto-archiver --mode full
```

------------

### Running a Local Install

### Example invocations

Once all your [local requirements](#installing-local-requirements) are correctly installed, the

```bash
# all the configurations come from ./secrets/orchestration.yaml
auto-archiver --config secrets/orchestration.yaml
# uses the same configurations but for another google docs sheet 
# with a header on row 2 and with some different column names
# notice that columns is a dictionary so you need to pass it as JSON and it will override only the values provided
auto-archiver --config secrets/orchestration.yaml --gsheet_feeder.sheet="use it on another sheets doc" --gsheet_feeder.header=2 --gsheet_feeder.columns='{"url": "link"}'
# all the configurations come from orchestration.yaml and specifies that s3 files should be private
auto-archiver --config secrets/orchestration.yaml --s3_storage.private=1
```
