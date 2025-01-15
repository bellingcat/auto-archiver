import pytest
from pathlib import Path

from auto_archiver.archivers.youtubedl_archiver import YoutubeDLArchiver

from .test_archiver_base import TestArchiverBase

class TestYoutubeDLArchiver(TestArchiverBase):
    """Tests YoutubeDL Archiver
    """
    archiver_class = YoutubeDLArchiver
    config = {
        'subtitles': False,
        'comments': False,
        'livestreams': False,
        'live_from_start': False,
        'end_means_success': True,
        'allow_playlist': False,
        'max_downloads': "inf",
        'proxy': None,
        'cookies_from_browser': False,
        'cookie_file': None,
        }

    @pytest.mark.parametrize("url, is_suitable", [
        ("https://www.youtube.com/watch?v=5qap5aO4i9A", True),
        ("https://www.tiktok.com/@funnycats0ftiktok/video/7345101300750748970?lang=en", True),
        ("https://www.instagram.com/p/CU1J9JYJ9Zz/", True),
        ("https://www.facebook.com/nytimes/videos/10160796550110716", True),
        ("https://www.twitch.tv/videos/1167226570", True),
        ("https://bellingcat.com/news/2021/10/08/ukrainian-soldiers-are-being-killed-by-landmines-in-the-donbas/", True),
        ("https://google.com", True)])
    def test_suitable_urls(self, make_item, url, is_suitable):
        """
            Note: expected behaviour is to return True for all URLs, as YoutubeDLArchiver should be able to handle all URLs
            This behaviour may be changed in the future (e.g. if we want the youtubedl archiver to just handle URLs it has extractors for,
            and then if and only if all archivers fails, does it fall back to the generic archiver)
        """
        assert self.archiver.suitable(make_item(url)) == is_suitable

    @pytest.mark.download
    def test_download_tiktok(self, make_item):
        item = make_item("https://www.tiktok.com/@funnycats0ftiktok/video/7345101300750748970")
        result = self.archiver.download(item)
        assert result.get_url() == "https://www.tiktok.com/@funnycats0ftiktok/video/7345101300750748970"
    
    @pytest.mark.download
    def test_download_youtube(self, make_item):
        # url https://www.youtube.com/watch?v=5qap5aO4i9A
        item = make_item("https://www.youtube.com/watch?v=J---aiyznGQ")
        result = self.archiver.download(item)
        assert result.get_url() == "https://www.youtube.com/watch?v=J---aiyznGQ"
        assert result.get_title() == "Keyboard Cat! - THE ORIGINAL!"
        assert result.get('description') == "Buy NEW Keyboard Cat Merch! https://keyboardcat.creator-spring.com\n\nxo Keyboard Cat memes make your day better!\nhttp://www.keyboardcatstore.com/\nhttps://www.facebook.com/thekeyboardcat\nhttp://www.charlieschmidt.com/"
        assert len(result.media) == 2
        assert Path(result.media[0].filename).name == "J---aiyznGQ.webm"
        assert Path(result.media[1].filename).name == "hqdefault.jpg"