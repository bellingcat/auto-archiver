### Testing

Tests are split using `pytest.mark` into 'core' and 'download' tests. Download tests will hit the network and make API calls (e.g. Twitter, Bluesky etc.) and should be run regularly to make sure that APIs have not changed.

Tests can be run as follows:
```
# run core tests
pytest -ra -v -m "not download" # or poetry run pytest -ra -v -m "not download"
# run download tests
pytest -ra -v -m "download" # or poetry run pytest -ra -v -m "download"
# run all tests
pytest -ra -v # or poetry run pytest -ra -v
```