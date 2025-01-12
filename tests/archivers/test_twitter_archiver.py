import unittest
import datetime

from auto_archiver.archivers.twitter_archiver import TwitterArchiver

from .test_archiver_base import TestArchiverBase


class TestTwitterArchiver(TestArchiverBase, unittest.TestCase):

    archiver_class = TwitterArchiver
    config = {}
    
    def test_sanitize_url(self):

        # should expand t.co URLs
        t_co_url = "https://t.co/yl3oOJatFp"
        t_co_resolved_url = "https://www.bellingcat.com/category/resources/"
        self.assertEqual(t_co_resolved_url, self.archiver.sanitize_url(t_co_url))

        # shouldn't alter valid x URLs
        x_url = "https://x.com/bellingcat/status/1874097816571961839"
        self.assertEqual(x_url, self.archiver.sanitize_url(x_url))

        # shouldn't alter valid twitter.com URLs
        twitter_url = "https://twitter.com/bellingcat/status/1874097816571961839"
        self.assertEqual(twitter_url, self.archiver.sanitize_url(twitter_url))

        # should strip tracking params
        tracking_url = "https://twitter.com/bellingcat/status/1874097816571961839?s=20&t=3d0g4ZQis7dCbSDg-mE7-w"
        self.assertEqual("https://twitter.com/bellingcat/status/1874097816571961839", self.archiver.sanitize_url(tracking_url))

        # shouldn't alter non-twitter/x URLs
        test_url = "https://www.bellingcat.com/category/resources/"
        self.assertEqual(test_url, self.archiver.sanitize_url(test_url))

        # shouldn't strip params from non-twitter/x URLs
        test_url = "https://www.bellingcat.com/category/resources/?s=20&t=3d0g4ZQis7dCbSDg-mE7-w"
        self.assertEqual(test_url, self.archiver.sanitize_url(test_url))

    
    def test_get_username_tweet_id_from_url(self):

        # test valid twitter URL
        url = "https://twitter.com/bellingcat/status/1874097816571961839"
        username, tweet_id = self.archiver.get_username_tweet_id(url)
        self.assertEqual("bellingcat", username)
        self.assertEqual("1874097816571961839", tweet_id)

        # test valid x URL
        url = "https://x.com/bellingcat/status/1874097816571961839"
        username, tweet_id = self.archiver.get_username_tweet_id(url)
        self.assertEqual("bellingcat", username)
        self.assertEqual("1874097816571961839", tweet_id)

        # test invalid URL
        # TODO: should this return None, False or raise an exception? Right now it returns False
        url = "https://www.bellingcat.com/category/resources/"
        username, tweet_id = self.archiver.get_username_tweet_id(url)
        self.assertFalse(username)
        self.assertFalse(tweet_id)

    def test_youtube_dlp_archiver(self):

        url = "https://x.com/bellingcat/status/1874097816571961839"
        post = self.archiver.download_yt_dlp(self.create_item(url), url, "1874097816571961839")
        self.assertTrue(post)
        self.assertValidResponseMetadata(
            post,
            "As 2024 comes to a close, here’s some examples of what Bellingcat investigated per month in our 10th year! 🧵",
            datetime.datetime(2024, 12, 31, 14, 18, 33, tzinfo=datetime.timezone.utc)
        )
        breakpoint()


    def test_download_media_with_images(self):
        # url https://twitter.com/MeCookieMonster/status/1617921633456640001?s=20&t=3d0g4ZQis7dCbSDg-mE7-w
        
        post = self.archiver.download()

        # just make sure twitter haven't changed their format, images should be under "record/embed/media/images"
        # there should be 2 images
        self.assertTrue("record" in post)
        self.assertTrue("embed" in post["record"])
        self.assertTrue("media" in post["record"]["embed"])
        self.assertTrue("images" in post["record"]["embed"]["media"])
        self.assertEqual(len(post["record"]["embed"]["media"]["images"]), 2)

        # try downloading the media files
        media = self.archiver.download(post)
        self.assertEqual(len(media), 2)

        # check the IDs
        self.assertTrue("bafkreiflrkfihcvwlhka5tb2opw2qog6gfvywsdzdlibveys2acozh75tq" in media[0].get('src'))
        self.assertTrue("bafkreibsprmwchf7r6xcstqkdvvuj3ijw7efciw7l3y4crxr4cmynseo7u" in media[1].get('src'))