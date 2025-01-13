import unittest
import datetime
import pytest

from auto_archiver.archivers.twitter_archiver import TwitterArchiver

from .test_archiver_base import TestArchiverBase

class TestTwitterArchiver(TestArchiverBase, unittest.TestCase):

    archiver_class = TwitterArchiver
    config = {}
    
    def test_sanitize_url(self):

        # should expand t.co URLs
        t_co_url = "https://t.co/yl3oOJatFp"
        t_co_resolved_url = "https://www.bellingcat.com/category/resources/"
        assert t_co_resolved_url == self.archiver.sanitize_url(t_co_url)

        # shouldn't alter valid x URLs
        x_url = "https://x.com/bellingcat/status/1874097816571961839"
        assert x_url == self.archiver.sanitize_url(x_url)

        # shouldn't alter valid twitter.com URLs
        twitter_url = "https://twitter.com/bellingcat/status/1874097816571961839"
        assert twitter_url == self.archiver.sanitize_url(twitter_url)

        # should strip tracking params
        tracking_url = "https://twitter.com/bellingcat/status/1874097816571961839?s=20&t=3d0g4ZQis7dCbSDg-mE7-w"
        assert "https://twitter.com/bellingcat/status/1874097816571961839" == self.archiver.sanitize_url(tracking_url)

        # shouldn't alter non-twitter/x URLs
        test_url = "https://www.bellingcat.com/category/resources/"
        assert test_url == self.archiver.sanitize_url(test_url)

        # shouldn't strip params from non-twitter/x URLs
        test_url = "https://www.bellingcat.com/category/resources/?s=20&t=3d0g4ZQis7dCbSDg-mE7-w"
        assert test_url == self.archiver.sanitize_url(test_url)

    
    def test_get_username_tweet_id_from_url(self):

        # test valid twitter URL
        url = "https://twitter.com/bellingcat/status/1874097816571961839"
        username, tweet_id = self.archiver.get_username_tweet_id(url)
        assert "bellingcat" == username
        assert "1874097816571961839" == tweet_id

        # test valid x URL
        url = "https://x.com/bellingcat/status/1874097816571961839"
        username, tweet_id = self.archiver.get_username_tweet_id(url)
        assert "bellingcat" == username
        assert "1874097816571961839" == tweet_id

        # test invalid URL
        # TODO: should this return None, False or raise an exception? Right now it returns False
        url = "https://www.bellingcat.com/category/resources/"
        username, tweet_id = self.archiver.get_username_tweet_id(url)
        assert not username
        assert not tweet_id

    @pytest.mark.download
    def test_youtube_dlp_archiver(self):

        url = "https://x.com/bellingcat/status/1874097816571961839"
        post = self.archiver.download_yt_dlp(self.create_item(url), url, "1874097816571961839")
        assert post
        self.assertValidResponseMetadata(
            post,
            "As 2024 comes to a close, here’s some examples of what Bellingcat investigated per month in our 10th year! 🧵",
            datetime.datetime(2024, 12, 31, 14, 18, 33, tzinfo=datetime.timezone.utc),
            "twitter-ytdl"
        )

    @pytest.mark.download
    def test_download_tweet_no_media(self):
        # url https://twitter.com/MeCookieMonster/status/1617921633456640001?s=20&t=3d0g4ZQis7dCbSDg-mE7-w
        
        item = self.create_item("https://twitter.com/MeCookieMonster/status/1617921633456640001?s=20&t=3d0g4ZQis7dCbSDg-mE7-w")
        post = self.archiver.download(item)

        self.assertValidResponseMetadata(
            post,
            "Onion rings are just vegetable donuts.",
            datetime.datetime(2023, 1, 24, 16, 25, 51, tzinfo=datetime.timezone.utc),
            "twitter-ytdl"
        )

    @pytest.mark.download
    def test_download_sensitive_media(self):

        """Download tweets with sensitive media
        
        Note: currently failing, youtube-dlp requres logged in users"""


        test_data = [
            ("https://x.com/SozinhoRamalho/status/1876710769913450647", "ignore tweet, testing sensitivity warning nudity", datetime.datetime(2024, 12, 31, 14, 18, 33, tzinfo=datetime.timezone.utc), "image_hash"),
            ("https://x.com/SozinhoRamalho/status/1876710875475681357", "ignore tweet, testing sensitivity warning violence", datetime.datetime(2024, 12, 31, 14, 18, 33, tzinfo=datetime.timezone.utc), "image_hash"),
            ("https://x.com/SozinhoRamalho/status/1876711053813227618", "ignore tweet, testing sensitivity warning sensitive", datetime.datetime(2024, 12, 31, 14, 18, 33, tzinfo=datetime.timezone.utc), "image_hash"),
            ("https://x.com/SozinhoRamalho/status/1876711141314801937", "ignore tweet, testing sensitivity warning nudity, violence, sensitivity", datetime.datetime(2024, 12, 31, 14, 18, 33, tzinfo=datetime.timezone.utc), "image_hash")
        ]

        for url, title, timestamp, image_hash in test_data:
            post = self.archiver.download(self.create_item(url))
            self.assertValidResponseMetadata(
                post,
                title,
                timestamp
            )
            assert len(post.media) == 1
            assert post.media[0].hash == image_hash