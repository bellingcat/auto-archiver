import pytest
from auto_archiver.core.metadata import Metadata

@pytest.fixture
def make_item():
    def _make_item(url: str, **kwargs) -> Metadata:
        item = Metadata().set_url(url)
        for key, value in kwargs.items():
            item.set(key, value)
        return item

    return _make_item