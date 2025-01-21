import pytest

from auto_archiver.core import Metadata
from auto_archiver.core import Step
from auto_archiver.core.metadata import Metadata
from auto_archiver.archivers.archiver import Archiver
class TestArchiverBase(object):

    archiver_class: str = None
    config: dict = None

    @pytest.fixture(autouse=True)
    def setup_archiver(self):
        assert self.archiver_class is not None, "self.archiver_class must be set on the subclass"
        assert self.config is not None, "self.config must be a dict set on the subclass"
        self.archiver: Archiver = self.archiver_class({self.archiver_class.name: self.config})
    
    def assertValidResponseMetadata(self, test_response: Metadata, title: str, timestamp: str, status: str = ""):
        assert test_response is not False

        if not status:
            assert test_response.is_success()
        else:
            assert status == test_response.status

        assert title == test_response.get_title()
        assert timestamp, test_response.get("timestamp")
