# Release Process

```{note} This is a work in progress.
```
### Update the project version

Update the version number in the project file: [pyproject.toml](../../pyproject.toml) following SemVer:
```toml
[project]
name = "auto-archiver"
version = "0.1.1"
```
Then commit and push the changes.

* The package version is automatically updated in PyPi using the workflow [python-publish.yml](../../.github/workflows/python-publish.yml)
* A Docker image is automatically pushed with the git tag to dockerhub using the workflow [docker-publish.yml](../../.github/workflows/docker-publish.yml)

### Create the release on Git

The release needs a git tag which should match the project version number, prefixed with a 'v'. For example, if the project version is `0.1.1`, the git tag should be `v0.1.1`.
This can be done the usual way, or created within the Github UI when you create the release.

Go to GitHub releases > new release > create the release with the new tag and the release notes.


manual release to docker hub
  * `docker image tag auto-archiver bellingcat/auto-archiver:latest`
  * `docker push bellingcat/auto-archiver`


### Building the Settings Page

The Settings page is built as part of the python-publish workflow and packaged within the app.