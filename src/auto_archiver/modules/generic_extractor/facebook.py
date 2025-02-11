from .dropin import GenericDropin


class Facebook(GenericDropin):
    def extract_post(self, url: str, ie_instance):
        video_id = ie_instance._match_valid_url(url).group('id')
        ie_instance._download_webpage(
            url.replace('://m.facebook.com/', '://www.facebook.com/'), video_id)
        webpage = ie_instance._download_webpage(url, ie_instance._match_valid_url(url).group('id'))

        # TODO: fix once https://github.com/yt-dlp/yt-dlp/pull/12275 is merged
        post_data = ie_instance._extract_metadata(webpage)
        return post_data
    
    def create_metadata(self, post: dict, ie_instance, archiver, url):
        metadata = archiver.create_metadata(url)
        metadata.set_title(post.get('title')).set_content(post.get('description')).set_post_data(post)
        return metadata