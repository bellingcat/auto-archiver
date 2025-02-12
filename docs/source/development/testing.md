# Testing

`pytest` is used for testing. There are two main types of tests:

1. 'core' tests which should be run on every change
2. 'download' tests which hit the network. These tests will do things like make API calls (e.g. Twitter, Bluesky etc.) and should be run regularly to make sure that APIs have not changed.


## Running Tests 

1. Make sure you've installed the dev dependencies with `pytest install --with dev`
2. Tests can be run as follows:
```
#### Command prefix of 'poetry run' removed here for simplicity
# run core tests
pytest -ra -v -m "not download"
# run download tests
pytest -ra -v -m "download"
# run all tests
pytest -ra -v
```