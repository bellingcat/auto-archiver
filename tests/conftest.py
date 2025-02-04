"""
pytest conftest file, for shared fixtures and configuration
"""

from typing import Dict, Tuple

import pytest
from auto_archiver.core.metadata import Metadata

# Test names inserted into this list will be run last. This is useful for expensive/costly tests
# that you only want to run if everything else succeeds (e.g. API calls). The order here is important
# what comes first will be run first (at the end of all other tests not mentioned)
# format is the name of the module (python file) without the .py extension
TESTS_TO_RUN_LAST = ['test_twitter_api_archiver']


@pytest.fixture
def make_item():
    def _make_item(url: str, **kwargs) -> Metadata:
        item = Metadata().set_url(url)
        for key, value in kwargs.items():
            item.set(key, value)
        return item

    return _make_item



def pytest_collection_modifyitems(items):
    module_mapping = {item: item.module.__name__.split(".")[-1] for item in items}

    sorted_items = items.copy()
    # Iteratively move tests of each module to the end of the test queue
    for module in TESTS_TO_RUN_LAST:
        if module in module_mapping.values():
            for item in sorted_items:
                if module_mapping[item] == module:
                    sorted_items.remove(item)
                    sorted_items.append(item)

    items[:] = sorted_items



# Incremental testing - fail tests in a class if any previous test fails
# taken from https://docs.pytest.org/en/latest/example/simple.html#incremental-testing-test-steps

# store history of failures per test class name and per index in parametrize (if parametrize used)
_test_failed_incremental: Dict[str, Dict[Tuple[int, ...], str]] = {}

def pytest_runtest_makereport(item, call):
    if "incremental" in item.keywords:
        # incremental marker is used
        if call.excinfo is not None:
            # the test has failed
            # retrieve the class name of the test
            cls_name = str(item.cls)
            # retrieve the index of the test (if parametrize is used in combination with incremental)
            parametrize_index = (
                tuple(item.callspec.indices.values())
                if hasattr(item, "callspec")
                else ()
            )
            # retrieve the name of the test function
            test_name = item.originalname or item.name
            # store in _test_failed_incremental the original name of the failed test
            _test_failed_incremental.setdefault(cls_name, {}).setdefault(
                parametrize_index, test_name
            )


def pytest_runtest_setup(item):
    if "incremental" in item.keywords:
        # retrieve the class name of the test
        cls_name = str(item.cls)
        # check if a previous test has failed for this class
        if cls_name in _test_failed_incremental:
            # retrieve the name of the first test function to fail for this class name and index
            test_name = _test_failed_incremental[cls_name].get((), None)
            # if name found, test has failed for the combination of class name & test name
            if test_name is not None:
                pytest.xfail(f"previous test failed ({test_name})")