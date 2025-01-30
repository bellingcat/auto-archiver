import pytest

from auto_archiver.core.metadata import Metadata
from auto_archiver.core.extractor import Extractor

class TestExtractorBase(object):

    extractor_module: str = None
    config: dict = None

    @pytest.fixture(autouse=True)
    def setup_extractor(self, setup_module):
        assert self.extractor_module is not None, "self.extractor_module must be set on the subclass"
        assert self.config is not None, "self.config must be a dict set on the subclass"

        self.extractor: Extractor = setup_module(self.extractor_module, self.config)
    
    def assertValidResponseMetadata(self, test_response: Metadata, title: str, timestamp: str, status: str = ""):
        assert test_response is not False

        if not status:
            assert test_response.is_success()
        else:
            assert status == test_response.status

        assert title == test_response.get_title()
        assert timestamp, test_response.get("timestamp")
