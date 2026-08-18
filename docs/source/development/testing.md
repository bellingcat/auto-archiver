# Testing

`pytest` is used for testing. There are two main types of tests:

1. 'core' tests which should be run on every change
2. 'download' tests which hit the network. These tests will do things like make API calls (e.g. Twitter, Bluesky etc.) and should be run regularly to make sure that APIs have not changed, they take longer.


## Running Tests 

1. Make sure you've installed the dev dependencies with `poetry install --with dev`
2. Tests can be run as follows:
```{code} bash
#### Command prefix of 'poetry run' removed here for simplicity
# run core tests
pytest -ra -v -m "not download"
# run download tests
pytest -ra -v -m "download"
# run all tests
pytest -ra -v


# run a specific test file
pytest -ra -v tests/test_file.py
# run a specific test function
pytest -ra -v tests/test_file.py::test_function_name
```

3. Some tests require environment variables to be set. You can use the example `tests/.env.test.example` file as a template. Copy it to `tests/.env.test` and fill in the required values. This file will be loaded automatically by `pytest`.
```{code} bash
cp tests/.env.test.example tests/.env.test
```
