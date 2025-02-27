# Release Process

```{note} This is a work in progress.
```

1. Update the version number in [version.py](src/auto_archiver/version.py)
2. Go to github releases > new release > use `vx.y.z` for matching version notation
   1. package is automatically updated in pypi
   2. docker image is automatically pushed to dockerhub



manual release to docker hub
  * `docker image tag auto-archiver bellingcat/auto-archiver:latest`
  * `docker push bellingcat/auto-archiver`


### Building the Settings Page

The Settings page is built as part of the python-publish workflow and packaged within the app.