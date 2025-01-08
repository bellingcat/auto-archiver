from auto_archiver.archivers.bluesky_archiver import BlueskyArchiver
from vcr.unittest import VCRMixin
import unittest

class TestBlueskyArchiver(VCRMixin, unittest.TestCase):
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
        assert "record" in post
        assert "embed" in post["record"]
        assert "media" in post["record"]["embed"]
        assert "images" in post["record"]["embed"]["media"]
        assert len(post["record"]["embed"]["media"]["images"]) == 2

        # try downloading the media files
        media = self.bsky._download_bsky_embeds(post)
        assert len(media) == 2

        # check the IDs
        assert "bafkreiflrkfihcvwlhka5tb2opw2qog6gfvywsdzdlibveys2acozh75tq" in media[0].get('src')
        assert "bafkreibsprmwchf7r6xcstqkdvvuj3ijw7efciw7l3y4crxr4cmynseo7u" in media[1].get('src')

    def test_download_post_with_single_image(self):
        # url https://bsky.app/profile/bellingcat.com/post/3lcxcpgt6j42l
        post = self.bsky._get_post_from_uri("https://bsky.app/profile/bellingcat.com/post/3lcxcpgt6j42l")

        # just make sure bsky haven't changed their format, images should be under "record/embed/images"
        # there should be 1 image
        assert "record" in post
        assert "embed" in post["record"]
        assert "images" in post["record"]["embed"]
        assert len(post["record"]["embed"]["images"]) == 1

        media = self.bsky._download_bsky_embeds(post)
        assert len(media) == 1

        # check the ID 
        assert "bafkreihljdtomy4yulx4nfxuqdatlgvdg45vxdmjzzhclsd4ludk7zfma4" in media[0].get('src')
                         

    def test_download_post_with_video(self):
        # url https://bsky.app/profile/bellingcat.com/post/3le2l4gsxlk2i
        post = self.bsky._get_post_from_uri("https://bsky.app/profile/bellingcat.com/post/3le2l4gsxlk2i")

        # just make sure bsky haven't changed their format, video should be under "record/embed/video"
        assert "record" in post
        assert "embed" in post["record"]
        assert "video" in post["record"]["embed"]

        media = self.bsky._download_bsky_embeds(post)
        assert len(media) == 1

        # check the ID
        assert "bafkreiaiskn2nt5cxjnxbgcqqcrnurvkr2ni3unekn6zvhvgr5nrqg6u2q" in media[0].get('src')

        