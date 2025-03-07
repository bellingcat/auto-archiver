# Release Process

```{note} This is a work in progress.
```

1. Update the version number in the project file: [pyproject.toml](../../pyproject.toml) following SemVer:
```toml
[project]
name = "auto-archiver"
version = "0.1.1"
```
Then commit and push the changes.

2. Next add a new git tag with the version number:
```shell
git tag -a v0.1.1
git push origin v0.1.1
```

* The package version is automatically updated in PyPi using the workflow [python-publish.yml](../../.github/workflows/python-publish.yml)
* A Docker image is automatically pushed with the git tag to dockerhub using the workflow [docker-publish.yml](../../.github/workflows/docker-publish.yml)


3. Go to GitHub releases > new release > and select the tag you just created. 


manual release to docker hub
  * `docker image tag auto-archiver bellingcat/auto-archiver:latest`
  * `docker push bellingcat/auto-archiver`


### Building the Settings Page

The Settings page is built as part of the python-publish workflow and packaged within the app.