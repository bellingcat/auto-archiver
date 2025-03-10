from typing import Type

import pytest

from auto_archiver.core.metadata import Metadata
from auto_archiver.core.storage import Storage


class TestStorageBase(object):
    module_name: str = None
    config: dict = None

    @pytest.fixture(autouse=True)
    def setup_storage(self, setup_module):
        assert self.module_name is not None, "self.module_name must be set on the subclass"
        assert self.config is not None, "self.config must be a dict set on the subclass"
        self.storage: Type[Storage] = setup_module(self.module_name, self.config)
