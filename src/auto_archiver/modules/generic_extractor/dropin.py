from typing import Type
from yt_dlp.extractor.common import InfoExtractor
from auto_archiver.core.metadata import Metadata
from auto_archiver.core.extractor import Extractor


class GenericDropin:
    """Base class for dropins for the generic extractor.

    In many instances, an extractor will exist in ytdlp, but it will only process videos.
    Dropins can be created and used to make use of the already-written private code of a
    specific extractor from ytdlp.

    The dropin should be able to handle the following methods:

    - `get_post_data`: This method should be able to extract the post data from the url and return it as a dict.
    - `create_metadata`: This method should be able to create a Metadata object from a post dict.

    Optional methods include:

    - `skip_ytdlp_download`: If you want to skip the ytdlp 'download' method all together, and do your own, then return True for this method.
                             This is useful in cases where ytdlp might not work properly for all of your posts
    - `keys_to_clean`: for the generic 'video_data' created by ytdlp (for video URLs), any additional fields you would like to clean out of the data before storing in metadata


    """

    extractor: Type[Extractor] = None

    def extract_post(self, url: str, ie_instance: InfoExtractor):
        """
        This method should return the post data from the url.
        """
        raise NotImplementedError("This method should be implemented in the subclass")

    def create_metadata(self, post: dict, ie_instance: InfoExtractor, archiver: Extractor, url: str) -> Metadata:
        """
        This method should create a Metadata object from the post data.
        """
        raise NotImplementedError("This method should be implemented in the subclass")

    def skip_ytdlp_download(self, url: str, ie_instance: InfoExtractor):
        """
        This method should return True if you want to skip the ytdlp download method.
        """
        return False

    def keys_to_clean(self, video_data: dict, info_extractor: InfoExtractor):
        """
        This method should return a list of strings (keys) to clean from the video_data dict.

        E.g. ["uploader", "uploader_id", "tiktok_specific_field"]
        """
        return []

    def download_additional_media(self, video_data: dict, info_extractor: InfoExtractor, metadata: Metadata):
        """
        This method should download any additional media from the post.
        """
        return metadata

    def suitable(self, url, info_extractor: InfoExtractor):
        """
        A method to allow dropins to override their InfoExtractor's 'suitable' method.
        Dropins should override this method and return True if the url is suitable for the extractor
        (based on being able to parse other URLs). See the `suitable_extractors` method in the
        `GenericExtractor` class for how this is implemented.

        The default behaviour of this method is to return the result of the InfoExtractor's 'suitable' method.

        ### Example: An example of where this is useful is for the FacebookIE extractor in yt-dlp. By default,
        it's 'suitable' method only returns True for video URLs. However, we can override this method in the
        Facebook dropin to return True for all Facebook URLs (photo/post types). This way, the Facebook dropin
        can be used for all Facebook URLs.
        """
        return info_extractor.suitable(url)
