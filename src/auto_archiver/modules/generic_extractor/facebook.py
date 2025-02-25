import re
from .dropin import GenericDropin
from auto_archiver.core.metadata import Metadata
from auto_archiver.core.media import Media

class Facebook(GenericDropin):
    
    def extract_post(self, url: str, ie_instance):
        post_id_regex = r'(?P<id>pfbid[A-Za-z0-9]+|\d+|t\.(\d+\/\d+))'
        post_id = re.search(post_id_regex, url).group('id')
        webpage = ie_instance._download_webpage(
            url.replace('://m.facebook.com/', '://www.facebook.com/'), post_id)

        # WARN: Will only work once https://github.com/yt-dlp/yt-dlp/pull/12275 is merged
        # TODO: For long posts, this _extract_metadata only seems to return the first 100 or so characters, followed by ...
        post_data = ie_instance._extract_metadata(webpage, post_id)
        return post_data

    def create_metadata(self, post: dict, ie_instance, archiver, url):
        result = Metadata()
        result.set_content(post.get('description', ''))
        result.set_title(post.get('title', ''))
        result.set('author', post.get('uploader', ''))
        result.set_url(url)
        return result
    
    def is_suitable(self, url, info_extractor):
        regex = r'(?:https?://(?:[\w-]+\.)?(?:facebook\.com||facebookwkhpilnemxj7asaniu7vnjjbiltxjqhye3mhbshg7kx5tfyd\.onion)/)'
        return re.match(regex, url)
    
    def skip_ytdlp_download(self, url: str, ie_instance):
        """
        Skip using the ytdlp download method for Facebook *photo* posts, they have a URL with an id of t.XXXXX/XXXXX
        """
        if re.search(r'/t.\d+/\d+', url):
            return True