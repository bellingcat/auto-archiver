from auto_archiver.archivers.bluesky_archiver import BlueskyArchiver
import unittest

class TestBlueskyArchiver(unittest.TestCase):
    """Tests Bluesky Archiver
    
    Note that these tests will download API responses from the bluesky API, so they may be slow.
    This is an intended feature, as we want to test to ensure the bluesky API format hasn't changed, 
    and also test the archiver's ability to download media.
    """

    # def _download_bsky_embeds(self, post):
    #     # method to override actual method, and monkey patch requests.get so as to not actually download
    #     # the media files
    #     old_requests_get = requests.get
    #     def mock_requests_get(*args, **kwargs):
    #         return {"status_code": 200, "json": lambda: {"data": "fake data"}}
    #     requests.get = mock_requests_get
    #     media = self.bsky._download_bsky_embeds(post)
    #     requests.get = old_requests_get
    #     return media

    def setUp(self):
        self.bsky = BlueskyArchiver({})
        return super().setUp()
    
    def test_download_media_with_images(self):
        # url https://bsky.app/profile/colborne.bsky.social/post/3lec2bqjc5s2y
        post = self.bsky._get_post_from_uri("https://bsky.app/profile/colborne.bsky.social/post/3lec2bqjc5s2y")

        # just make sure bsky haven't changed their format, images should be under "record/embed/media/images"
        # there should be 2 images
        self.assertTrue("record" in post)
        self.assertTrue("embed" in post["record"])
        self.assertTrue("media" in post["record"]["embed"])
        self.assertTrue("images" in post["record"]["embed"]["media"])
        self.assertEqual(len(post["record"]["embed"]["media"]["images"]), 2)

        # try downloading the media files
        media = self.bsky._download_bsky_embeds(post)
        self.assertEqual(len(media), 2)

        # check the IDs
        self.assertTrue("bafkreiflrkfihcvwlhka5tb2opw2qog6gfvywsdzdlibveys2acozh75tq" in media[0].get('src'))
        self.assertTrue("bafkreibsprmwchf7r6xcstqkdvvuj3ijw7efciw7l3y4crxr4cmynseo7u" in media[1].get('src'))

    def test_download_post_with_single_image(self):
        # url https://bsky.app/profile/bellingcat.com/post/3lcxcpgt6j42l
        post = self.bsky._get_post_from_uri("https://bsky.app/profile/bellingcat.com/post/3lcxcpgt6j42l")

        # just make sure bsky haven't changed their format, images should be under "record/embed/images"
        # there should be 1 image
        self.assertTrue("record" in post)
        self.assertTrue("embed" in post["record"])
        self.assertTrue("images" in post["record"]["embed"])
        self.assertEqual(len(post["record"]["embed"]["images"]), 1)

        media = self.bsky._download_bsky_embeds(post)
        self.assertEqual(len(media), 1)

        # check the ID 
        self.assertTrue("bafkreihljdtomy4yulx4nfxuqdatlgvdg45vxdmjzzhclsd4ludk7zfma4" in media[0].get('src'))
                         

    def test_download_post_with_video(self):
        # url https://bsky.app/profile/bellingcat.com/post/3le2l4gsxlk2i
        post = self.bsky._get_post_from_uri("https://bsky.app/profile/bellingcat.com/post/3le2l4gsxlk2i")

        # just make sure bsky haven't changed their format, video should be under "record/embed/video"
        self.assertTrue("record" in post)
        self.assertTrue("embed" in post["record"])
        self.assertTrue("video" in post["record"]["embed"])

        media = self.bsky._download_bsky_embeds(post)
        self.assertEqual(len(media), 1)

        # check the ID
        self.assertTrue("bafkreiaiskn2nt5cxjnxbgcqqcrnurvkr2ni3unekn6zvhvgr5nrqg6u2q" in media[0].get('src'))

        