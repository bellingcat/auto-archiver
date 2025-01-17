import pytest
from pathlib import Path
import datetime 
import os

from auto_archiver.archivers.generic_archiver import GenericArchiver

from .test_archiver_base import TestArchiverBase

class TestGenericArchiver(TestArchiverBase):
    """Tests Base Archiver
    """
    archiver_class = GenericArchiver
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
        assert self.archiver.suitable(url) == is_suitable

    @pytest.mark.download
    def test_download_tiktok(self, make_item):
        item = make_item("https://www.tiktok.com/@funnycats0ftiktok/video/7345101300750748970")
        result = self.archiver.download(item)
        assert result.get_url() == "https://www.tiktok.com/@funnycats0ftiktok/video/7345101300750748970"

    @pytest.mark.download
    def test_youtube_download(self, make_item):
        # url https://www.youtube.com/watch?v=5qap5aO4i9A
        item = make_item("https://www.youtube.com/watch?v=J---aiyznGQ")
        result = self.archiver.download(item)
        assert result.get_url() == "https://www.youtube.com/watch?v=J---aiyznGQ"
        assert result.get_title() == "Keyboard Cat! - THE ORIGINAL!"
        assert result.get('description') == "Buy NEW Keyboard Cat Merch! https://keyboardcat.creator-spring.com\n\nxo Keyboard Cat memes make your day better!\nhttp://www.keyboardcatstore.com/\nhttps://www.facebook.com/thekeyboardcat\nhttp://www.charlieschmidt.com/"
        assert len(result.media) == 2
        assert Path(result.media[0].filename).name == "J---aiyznGQ.webm"
        assert Path(result.media[1].filename).name == "hqdefault.jpg"

    @pytest.mark.download
    def test_bluesky_download_multiple_images(self, make_item):
        item = make_item("https://bsky.app/profile/colborne.bsky.social/post/3lec2bqjc5s2y")
        result = self.archiver.download(item)
        assert result is not False

    @pytest.mark.skip("ytdlp supports bluesky, but there's currently no way to extract info from pages without videos")
    @pytest.mark.download
    def test_bluesky_download_single_image(self, make_item):
        item = make_item("https://bsky.app/profile/colborne.bsky.social/post/3lcxcpgt6j42l")
        result = self.archiver.download(item)
        assert result is not False
    
    @pytest.mark.download
    def test_bluesky_download_no_media(self, make_item):
        item = make_item("https://bsky.app/profile/bellingcat.com/post/3lfphwmcs4c2z")
        result = self.archiver.download(item)
        assert result is not False

    @pytest.mark.download
    def test_bluesky_download_video(self, make_item):
        item = make_item("https://bsky.app/profile/bellingcat.com/post/3le2l4gsxlk2i")
        result = self.archiver.download(item)
        assert result is not False

    @pytest.mark.download
    def test_twitter_download_nonexistend_tweet(self, make_item):
        # this tweet does not exist
        url = "https://x.com/Bellingcat/status/17197025860711058"
        response = self.archiver.download(make_item(url))
        assert not response
    
    @pytest.mark.download
    def test_twitter_download_malformed_tweetid(self, make_item):
        # this tweet does not exist
        url = "https://x.com/Bellingcat/status/1719702a586071100058"
        response = self.archiver.download(make_item(url))
        assert not response

    @pytest.mark.download
    def test_twitter_download_tweet_no_media(self, make_item):
        
        item = make_item("https://twitter.com/MeCookieMonster/status/1617921633456640001?s=20&t=3d0g4ZQis7dCbSDg-mE7-w")
        post = self.archiver.download(item)

        self.assertValidResponseMetadata(
            post,
            "Onion rings are just vegetable donuts.",
            datetime.datetime(2023, 1, 24, 16, 25, 51, tzinfo=datetime.timezone.utc),
            "yt-dlp_Twitter: success"
        )
    
    @pytest.mark.download
    def test_twitter_download_video(self, make_item):
        url = "https://x.com/bellingcat/status/1871552600346415571"
        post = self.archiver.download(make_item(url))
        self.assertValidResponseMetadata(
            post,
            "Bellingcat - This month's Bellingchat Premium is with @KolinaKoltai. She reveals how she investigated a platform allowing users to create AI-generated child sexual abuse material and explains why it's crucial to investigate the people behind these services",
            datetime.datetime(2024, 12, 24, 13, 44, 46, tzinfo=datetime.timezone.utc)
        )

    @pytest.mark.xfail(reason="Currently failing, sensitive content requires logged in users/cookies - not yet implemented")
    @pytest.mark.download
    @pytest.mark.parametrize("url, title, timestamp, image_hash", [
            ("https://x.com/SozinhoRamalho/status/1876710769913450647", "ignore tweet, testing sensitivity warning nudity", datetime.datetime(2024, 12, 31, 14, 18, 33, tzinfo=datetime.timezone.utc), "image_hash"),
            ("https://x.com/SozinhoRamalho/status/1876710875475681357", "ignore tweet, testing sensitivity warning violence", datetime.datetime(2024, 12, 31, 14, 18, 33, tzinfo=datetime.timezone.utc), "image_hash"),
            ("https://x.com/SozinhoRamalho/status/1876711053813227618", "ignore tweet, testing sensitivity warning sensitive", datetime.datetime(2024, 12, 31, 14, 18, 33, tzinfo=datetime.timezone.utc), "image_hash"),
            ("https://x.com/SozinhoRamalho/status/1876711141314801937", "ignore tweet, testing sensitivity warning nudity, violence, sensitivity", datetime.datetime(2024, 12, 31, 14, 18, 33, tzinfo=datetime.timezone.utc), "image_hash"),
        ])
    def test_twitter_download_sensitive_media(self, url, title, timestamp, image_hash, make_item):

        """Download tweets with sensitive media"""

        post = self.archiver.download(make_item(url))
        self.assertValidResponseMetadata(
            post,
            title,
            timestamp
        )
        assert len(post.media) == 1
        assert post.media[0].hash == image_hash