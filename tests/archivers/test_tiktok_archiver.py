import pytest

from .test_archiver_base import TestArchiverBase
from auto_archiver.archivers.tiktok_archiver import TiktokArchiver

class TestBlueskyArchiver(TestArchiverBase):

    archiver_class = TiktokArchiver
    config = {}

    @pytest.mark.xfail(reason="Tiktok API is not working")
    @pytest.mark.download
    def test_download_video(self, make_item):
        # cat video
        url = "https://www.tiktok.com/@funnycats0ftiktok/video/7345101300750748970?lang=en"
        item = self.archiver.download(make_item(url))
        assert item.success