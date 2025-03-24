
# Upgrading

If an update is available, then you will see a message in the logs when you
run Auto Archiver. Here's what those logs look like:

```{code} bash
********* IMPORTANT: UPDATE AVAILABLE ********
A new version of auto-archiver is available (v0.13.6, you have 0.13.4)
Make sure to update to the latest version using: `pip install --upgrade auto-archiver`
```

Upgrading Auto Archiver depends on the way you installed it.

## Docker

To upgrade using docker, update the docker image with:

```
docker pull bellingcat/auto-archiver:latest 
```

## Pip

To upgrade the pip package, use:

```
pip install --upgrade auto-archiver
```

