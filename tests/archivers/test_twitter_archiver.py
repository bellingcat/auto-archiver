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

    def test_choose_variants(self):
        # taken from the response for url https://x.com/bellingcat/status/1871552600346415571
        variant_list = [{'content_type': 'application/x-mpegURL', 'url': 'https://video.twimg.com/ext_tw_video/1871551993677852672/pu/pl/ovWo7ux-bKROwYIC.m3u8?tag=12&v=e1b'},
                        {'bitrate': 256000, 'content_type': 'video/mp4', 'url': 'https://video.twimg.com/ext_tw_video/1871551993677852672/pu/vid/avc1/480x270/OqZIrKV0LFswMvxS.mp4?tag=12'},
                        {'bitrate': 832000, 'content_type': 'video/mp4', 'url': 'https://video.twimg.com/ext_tw_video/1871551993677852672/pu/vid/avc1/640x360/uiDZDSmZ8MZn9hsi.mp4?tag=12'},
                        {'bitrate': 2176000, 'content_type': 'video/mp4', 'url': 'https://video.twimg.com/ext_tw_video/1871551993677852672/pu/vid/avc1/1280x720/6Y340Esh568WZnRZ.mp4?tag=12'}
                        ]
        chosen_variant = self.archiver.choose_variant(variant_list)
        assert chosen_variant == variant_list[3]

    def test_reverse_engineer_token(self):
        # see Vercel's implementation here: https://github.com/vercel/react-tweet/blob/main/packages/react-tweet/src/api/fetch-tweet.ts#L27C1-L31C2
        # and the discussion here: https://github.com/JustAnotherArchivist/snscrape/issues/996#issuecomment-2211358215

        for tweet_id, real_token in [
            ("1874097816571961839", "4jjngwkifa"),
            ("1674700676612386816", "42586mwa3uv"),
            ("1877747914073620506", "4jv4aahw36n"),
            ("1876710769913450647", "4jruzjz5lux"),
            ("1346554693649113090", "39ibqxei7mo"),]:
            generated_token = self.archiver.generate_token(tweet_id)
            self.assertEqual(real_token, generated_token)

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
    def test_syndication_archiver(self):

        url = "https://x.com/bellingcat/status/1874097816571961839"
        post = self.archiver.download_syndication(self.create_item(url), url, "1874097816571961839")
        self.assertTrue(post)
        self.assertValidResponseMetadata(
            post,
            "As 2024 comes to a close, here’s some examples of what Bellingcat investigated per month in our 10th year! 🧵",
            datetime.datetime(2024, 12, 31, 14, 18, 33, tzinfo=datetime.timezone.utc)
        )

    @pytest.mark.download
    def test_download_nonexistend_tweet(self):
        # this tweet does not exist
        url = "https://x.com/Bellingcat/status/17197025860711058"
        response = self.archiver.download(self.create_item(url))
        self.assertFalse(response)
    
    @pytest.mark.download
    def test_download_malformed_tweetid(self):
        # this tweet does not exist
        url = "https://x.com/Bellingcat/status/1719702586071100058"
        response = self.archiver.download(self.create_item(url))
        self.assertFalse(response)

    @pytest.mark.download
    def test_download_tweet_no_media(self):
        
        item = self.create_item("https://twitter.com/MeCookieMonster/status/1617921633456640001?s=20&t=3d0g4ZQis7dCbSDg-mE7-w")
        post = self.archiver.download(item)

        self.assertValidResponseMetadata(
            post,
            "Onion rings are just vegetable donuts.",
            datetime.datetime(2023, 1, 24, 16, 25, 51, tzinfo=datetime.timezone.utc),
            "twitter-ytdl"
        )
    
    @pytest.mark.download
    def test_download_video(self):
        url = "https://x.com/bellingcat/status/1871552600346415571"

        post = self.archiver.download(self.create_item(url))
        self.assertValidResponseMetadata(
            post,
            "This month's Bellingchat Premium is with @KolinaKoltai. She reveals how she investigated a platform allowing users to create AI-generated child sexual abuse material and explains why it's crucial to investigate the people behind these services https://t.co/SfBUq0hSD0 https://t.co/rIHx0WlKp8",
            datetime.datetime(2024, 12, 24, 13, 44, 46, tzinfo=datetime.timezone.utc)
        )

    @pytest.mark.download
    def test_download_sensitive_media(self):

        """Download tweets with sensitive media
        
        Note: currently failing, youtube-dlp requres logged in users + download_syndication requires logging in"""

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