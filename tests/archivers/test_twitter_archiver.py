import datetime
import pytest

from auto_archiver.archivers.twitter_archiver import TwitterArchiver

from .test_archiver_base import TestArchiverBase

class TestTwitterArchiver(TestArchiverBase):

    archiver_class = TwitterArchiver
    config = {}
    @pytest.mark.parametrize("url, expected", [
        ("https://t.co/yl3oOJatFp", "https://www.bellingcat.com/category/resources/"),  # t.co URL
        ("https://x.com/bellingcat/status/1874097816571961839", "https://x.com/bellingcat/status/1874097816571961839"), # x.com urls unchanged
        ("https://twitter.com/bellingcat/status/1874097816571961839", "https://twitter.com/bellingcat/status/1874097816571961839"), # twitter urls unchanged
        ("https://twitter.com/bellingcat/status/1874097816571961839?s=20&t=3d0g4ZQis7dCbSDg-mE7-w", "https://twitter.com/bellingcat/status/1874097816571961839"), # strip tracking params
        ("https://www.bellingcat.com/category/resources/", "https://www.bellingcat.com/category/resources/"), # non-twitter/x urls unchanged
        ("https://www.bellingcat.com/category/resources/?s=20&t=3d0g4ZQis7dCbSDg-mE7-w", "https://www.bellingcat.com/category/resources/?s=20&t=3d0g4ZQis7dCbSDg-mE7-w"), # shouldn't strip params from non-twitter/x URLs
    ])
    def test_sanitize_url(self, url, expected):
        assert expected == self.archiver.sanitize_url(url)
    
    @pytest.mark.parametrize("url, exptected_username, exptected_tweetid", [
        ("https://twitter.com/bellingcat/status/1874097816571961839", "bellingcat", "1874097816571961839"),
        ("https://x.com/bellingcat/status/1874097816571961839", "bellingcat", "1874097816571961839"),
        ("https://www.bellingcat.com/category/resources/", False, False)
        ])

    def test_get_username_tweet_id_from_url(self, url, exptected_username, exptected_tweetid):
    
        username, tweet_id = self.archiver.get_username_tweet_id(url)
        assert exptected_username == username
        assert exptected_tweetid == tweet_id
    
    def test_choose_variants(self):
        # taken from the response for url https://x.com/bellingcat/status/1871552600346415571
        variant_list = [{'content_type': 'application/x-mpegURL', 'url': 'https://video.twimg.com/ext_tw_video/1871551993677852672/pu/pl/ovWo7ux-bKROwYIC.m3u8?tag=12&v=e1b'},
                        {'bitrate': 256000, 'content_type': 'video/mp4', 'url': 'https://video.twimg.com/ext_tw_video/1871551993677852672/pu/vid/avc1/480x270/OqZIrKV0LFswMvxS.mp4?tag=12'},
                        {'bitrate': 832000, 'content_type': 'video/mp4', 'url': 'https://video.twimg.com/ext_tw_video/1871551993677852672/pu/vid/avc1/640x360/uiDZDSmZ8MZn9hsi.mp4?tag=12'},
                        {'bitrate': 2176000, 'content_type': 'video/mp4', 'url': 'https://video.twimg.com/ext_tw_video/1871551993677852672/pu/vid/avc1/1280x720/6Y340Esh568WZnRZ.mp4?tag=12'}
                        ]
        chosen_variant = self.archiver.choose_variant(variant_list)
        assert chosen_variant == variant_list[3]
    
    @pytest.mark.parametrize("tweet_id, expected_token", [
        ("1874097816571961839", "4jjngwkifa"),
        ("1674700676612386816", "42586mwa3uv"),
        ("1877747914073620506", "4jv4aahw36n"),
        ("1876710769913450647", "4jruzjz5lux"),
        ("1346554693649113090", "39ibqxei7mo")
        ])
    def test_reverse_engineer_token(self, tweet_id, expected_token):
        # see Vercel's implementation here: https://github.com/vercel/react-tweet/blob/main/packages/react-tweet/src/api/fetch-tweet.ts#L27C1-L31C2
        # and the discussion here: https://github.com/JustAnotherArchivist/snscrape/issues/996#issuecomment-2211358215

        generated_token = self.archiver.generate_token(tweet_id)
        assert expected_token == generated_token

    @pytest.mark.download
    def test_youtube_dlp_archiver(self, make_item):

        url = "https://x.com/bellingcat/status/1874097816571961839"
        post = self.archiver.download_yt_dlp(make_item(url), url, "1874097816571961839")
        assert post
        self.assertValidResponseMetadata(
            post,
            "As 2024 comes to a close, here’s some examples of what Bellingcat investigated per month in our 10th year! 🧵",
            datetime.datetime(2024, 12, 31, 14, 18, 33, tzinfo=datetime.timezone.utc),
            "twitter-ytdl"
        )
            
    @pytest.mark.download
    def test_syndication_archiver(self, make_item):

        url = "https://x.com/bellingcat/status/1874097816571961839"
        post = self.archiver.download_syndication(make_item(url), url, "1874097816571961839")
        assert post
        self.assertValidResponseMetadata(
            post,
            "As 2024 comes to a close, here’s some examples of what Bellingcat investigated per month in our 10th year! 🧵",
            datetime.datetime(2024, 12, 31, 14, 18, 33, tzinfo=datetime.timezone.utc)
        )

    @pytest.mark.download
    def test_download_nonexistend_tweet(self, make_item):
        # this tweet does not exist
        url = "https://x.com/Bellingcat/status/17197025860711058"
        response = self.archiver.download(make_item(url))
        assert not response
    
    @pytest.mark.download
    def test_download_malformed_tweetid(self, make_item):
        # this tweet does not exist
        url = "https://x.com/Bellingcat/status/1719702586071100058"
        response = self.archiver.download(make_item(url))
        assert not response

    @pytest.mark.download
    def test_download_tweet_no_media(self, make_item):
        
        item = make_item("https://twitter.com/MeCookieMonster/status/1617921633456640001?s=20&t=3d0g4ZQis7dCbSDg-mE7-w")
        post = self.archiver.download(item)

        self.assertValidResponseMetadata(
            post,
            "Onion rings are just vegetable donuts.",
            datetime.datetime(2023, 1, 24, 16, 25, 51, tzinfo=datetime.timezone.utc),
            "twitter-ytdl"
        )
    
    @pytest.mark.download
    def test_download_video(self, make_item):
        url = "https://x.com/bellingcat/status/1871552600346415571"
        post = self.archiver.download(make_item(url))
        self.assertValidResponseMetadata(
            post,
            "This month's Bellingchat Premium is with @KolinaKoltai. She reveals how she investigated a platform allowing users to create AI-generated child sexual abuse material and explains why it's crucial to investigate the people behind these services https://t.co/SfBUq0hSD0 https://t.co/rIHx0WlKp8",
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
    def test_download_sensitive_media(self, url, title, timestamp, image_hash, make_item):

        """Download tweets with sensitive media"""

        post = self.archiver.download(make_item(url))
        self.assertValidResponseMetadata(
            post,
            title,
            timestamp
        )
        assert len(post.media) == 1
        assert post.media[0].hash == image_hash