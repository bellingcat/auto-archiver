import os
import datetime
import hashlib
import pytest

from pytwitter.models.media import MediaVariant
from .test_extractor_base import TestExtractorBase
from auto_archiver.modules.twitter_api_extractor import TwitterApiExtractor


@pytest.mark.incremental
class TestTwitterApiExtractor(TestExtractorBase):

    extractor_module = 'twitter_api_extractor'

    config = {
        "bearer_tokens": [],
        "bearer_token": os.environ.get("TWITTER_BEARER_TOKEN", "TEST_KEY"),
        "consumer_key": os.environ.get("TWITTER_CONSUMER_KEY"),
        "consumer_secret": os.environ.get("TWITTER_CONSUMER_SECRET"),
        "access_token": os.environ.get("TWITTER_ACCESS_TOKEN"),
        "access_secret": os.environ.get("TWITTER_ACCESS_SECRET"),
    }

    @pytest.mark.parametrize("url, expected", [
        ("https://t.co/yl3oOJatFp", "https://www.bellingcat.com/category/resources/"),  # t.co URL
        ("https://x.com/bellingcat/status/1874097816571961839", "https://x.com/bellingcat/status/1874097816571961839"), # x.com urls unchanged
        ("https://twitter.com/bellingcat/status/1874097816571961839", "https://twitter.com/bellingcat/status/1874097816571961839"), # twitter urls unchanged
        ("https://twitter.com/bellingcat/status/1874097816571961839?s=20&t=3d0g4ZQis7dCbSDg-mE7-w", "https://twitter.com/bellingcat/status/1874097816571961839?s=20&t=3d0g4ZQis7dCbSDg-mE7-w"), # don't strip params from twitter urls (changed Jan 2025)
        ("https://www.bellingcat.com/category/resources/", "https://www.bellingcat.com/category/resources/"), # non-twitter/x urls unchanged
        ("https://www.bellingcat.com/category/resources/?s=20&t=3d0g4ZQis7dCbSDg-mE7-w", "https://www.bellingcat.com/category/resources/?s=20&t=3d0g4ZQis7dCbSDg-mE7-w"), # shouldn't strip params from non-twitter/x URLs
    ])
    def test_sanitize_url(self, url, expected):
        assert expected == self.extractor.sanitize_url(url)
    
    @pytest.mark.parametrize("url, exptected_username, exptected_tweetid", [
        ("https://twitter.com/bellingcat/status/1874097816571961839", "bellingcat", "1874097816571961839"),
        ("https://x.com/bellingcat/status/1874097816571961839", "bellingcat", "1874097816571961839"),
        ("https://www.bellingcat.com/category/resources/", False, False)
        ])
    def test_get_username_tweet_id_from_url(self, url, exptected_username, exptected_tweetid):
    
        username, tweet_id = self.extractor.get_username_tweet_id(url)
        assert exptected_username == username
        assert exptected_tweetid == tweet_id

    def test_choose_variants(self):
        # taken from the response for url https://x.com/bellingcat/status/1871552600346415571
        variant_list = [MediaVariant(content_type='application/x-mpegURL', url='https://video.twimg.com/ext_tw_video/1871551993677852672/pu/pl/ovWo7ux-bKROwYIC.m3u8?tag=12&v=e1b'),
                        MediaVariant(bit_rate=256000, content_type='video/mp4', url='https://video.twimg.com/ext_tw_video/1871551993677852672/pu/vid/avc1/480x270/OqZIrKV0LFswMvxS.mp4?tag=12'),
                        MediaVariant(bit_rate=832000, content_type='video/mp4', url='https://video.twimg.com/ext_tw_video/1871551993677852672/pu/vid/avc1/640x360/uiDZDSmZ8MZn9hsi.mp4?tag=12'),
                        MediaVariant(bit_rate=2176000, content_type='video/mp4', url='https://video.twimg.com/ext_tw_video/1871551993677852672/pu/vid/avc1/1280x720/6Y340Esh568WZnRZ.mp4?tag=12')
                        ]
        chosen_variant = self.extractor.choose_variant(variant_list)
        assert chosen_variant == variant_list[3]
    
    @pytest.mark.skipif(not os.environ.get("TWITTER_BEARER_TOKEN"), reason="No Twitter bearer token provided")
    @pytest.mark.download
    def test_download_nonexistent_tweet(self, make_item):
        # this tweet does not exist
        url = "https://x.com/Bellingcat/status/17197025860711058"
        response = self.extractor.download(make_item(url))
        assert not response

    @pytest.mark.skipif(not os.environ.get("TWITTER_BEARER_TOKEN"), reason="No Twitter bearer token provided")
    @pytest.mark.download
    def test_download_malformed_tweetid(self, make_item):
        # this tweet does not exist
        url = "https://x.com/Bellingcat/status/1719702586071100058"
        response = self.extractor.download(make_item(url))
        assert not response

    @pytest.mark.skipif(not os.environ.get("TWITTER_BEARER_TOKEN"), reason="No Twitter bearer token provided")
    @pytest.mark.download
    def test_download_tweet_no_media(self, make_item):
        
        item = make_item("https://twitter.com/MeCookieMonster/status/1617921633456640001?s=20&t=3d0g4ZQis7dCbSDg-mE7-w")
        post = self.extractor.download(item)

        self.assertValidResponseMetadata(
            post,
            "Onion rings are just vegetable donuts.",
            datetime.datetime(2023, 1, 24, 16, 25, 51, tzinfo=datetime.timezone.utc),
            "twitter-api: success"
        )

    @pytest.mark.skipif(not os.environ.get("TWITTER_BEARER_TOKEN"), reason="No Twitter bearer token provided")
    @pytest.mark.download
    def test_download_video(self, make_item):
        url = "https://x.com/bellingcat/status/1871552600346415571"
        post = self.extractor.download(make_item(url))
        self.assertValidResponseMetadata(
            post,
            "This month's Bellingchat Premium is with @KolinaKoltai. She reveals how she investigated a platform allowing users to create AI-generated child sexual abuse material and explains why it's crucial to investigate the people behind these services https://t.co/SfBUq0hSD0 https://t.co/rIHx0WlKp8",
            datetime.datetime(2024, 12, 24, 13, 44, 46, tzinfo=datetime.timezone.utc)
        )

    @pytest.mark.skipif(not os.environ.get("TWITTER_BEARER_TOKEN"), reason="No Twitter bearer token provided")
    @pytest.mark.parametrize("url, title, timestamp", [
            ("https://x.com/SozinhoRamalho/status/1876710769913450647", "ignore tweet, testing sensitivity warning nudity https://t.co/t3u0hQsSB1", datetime.datetime(2024, 12, 31, 14, 18, 33, tzinfo=datetime.timezone.utc)),
            ("https://x.com/SozinhoRamalho/status/1876710875475681357", "ignore tweet, testing sensitivity warning violence https://t.co/syYDSkpjZD", datetime.datetime(2024, 12, 31, 14, 18, 33, tzinfo=datetime.timezone.utc)),
            ("https://x.com/SozinhoRamalho/status/1876711053813227618", "ignore tweet, testing sensitivity warning sensitive https://t.co/XE7cRdjzYq", datetime.datetime(2024, 12, 31, 14, 18, 33, tzinfo=datetime.timezone.utc)),
            ("https://x.com/SozinhoRamalho/status/1876711141314801937", "ignore tweet, testing sensitivity warning nudity, violence, sensitivity https://t.co/YxCFbbhYE3", datetime.datetime(2024, 12, 31, 14, 18, 33, tzinfo=datetime.timezone.utc)),
        ])
    @pytest.mark.download
    def test_download_sensitive_media(self, url, title, timestamp, check_hash, make_item):

        """Download tweets with sensitive media"""

        post = self.extractor.download(make_item(url))
        self.assertValidResponseMetadata(
            post,
            title,
            timestamp
        )
        assert len(post.media) == 1
        # check the SHA1 hash (quick) of the media, to make sure it's valid
        check_hash(post.media[0].filename, "3eea9c03b2dcedd1eb9a169d8bfd1cf877996fab4961de019a96eb9d32d2d733")