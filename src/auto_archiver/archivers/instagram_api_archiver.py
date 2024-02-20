import re, requests
from datetime import datetime
from loguru import logger
from retrying import retry
from tqdm import tqdm

from . import Archiver
from ..core import Metadata
from ..core import Media

class InstagramAPIArchiver(Archiver):
    """
    Uses an https://github.com/subzeroid/instagrapi API deployment to fetch instagram posts data
    
    # TODO: improvement collect aggregates of locations[0].location and mentions for all posts
    """
    name = "instagram_api_archiver"

    global_pattern = re.compile(r"(?:(?:http|https):\/\/)?(?:www.)?(?:instagram.com)\/(stories(?:\/highlights)?|p|reel)?\/?([^\/\?]*)\/?(\d+)?")

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.assert_valid_string("access_token")
        self.assert_valid_string("api_endpoint")
        if self.api_endpoint[-1] == "/": self.api_endpoint = self.api_endpoint[:-1]

        self.full_profile = bool(self.full_profile)
        self.minimize_json_output = bool(self.minimize_json_output)

    @staticmethod
    def configs() -> dict:
        return {
            "access_token": {"default": None, "help": "a valid instagrapi-api token"},
            "api_endpoint": {"default": None, "help": "API endpoint to use"},
            "full_profile": {"default": False, "help": "if true, will download all posts, tagged posts, stories, and highlights for a profile, if false, will only download the profile pic and information."},
            "minimize_json_output": {"default": True, "help": "if true, will remove empty values from the json output"},
        }
    
    def download(self, item: Metadata) -> Metadata:
        url = item.get_url()

        url.replace("instagr.com", "instagram.com").replace("instagr.am", "instagram.com")
        insta_matches = self.global_pattern.findall(url)
        logger.info(f"{insta_matches=}")
        if not len(insta_matches) or len(insta_matches[0])!=3: return
        if len(insta_matches) > 1: 
            logger.warning(f"Multiple instagram matches found in {url=}, using the first one")
            return
        g1, g2, g3 = insta_matches[0][0], insta_matches[0][1], insta_matches[0][2]
        if g1 == "": return self.download_profile(item, g2)
        elif g1 == "p": return self.download_post(item, g2, context="post")
        elif g1 == "reel": return self.download_post(item, g2, context="reel")
        elif g1 == "stories/highlights": return self.download_highlights(item, g2)
        elif g1 == "stories": 
            if len(g3): return self.download_post(item, id=g3, context="story")
            return self.download_stories(item, g2)
        else: 
            logger.warning(f"Unknown instagram regex group match {g1=} found in {url=}")
            return
        
    @retry(wait_random_min=1000, wait_random_max=3000, stop_max_attempt_number=5)
    def call_api(self, path: str, params: dict) -> dict:
        headers = {
            "accept": "application/json",
            "x-access-key": self.access_token
        }
        logger.debug(f"calling {self.api_endpoint}/{path} with {params=}")
        return requests.get(f"{self.api_endpoint}/{path}", headers=headers, params=params).json()

    def cleanup_dict(self, d: dict | list) -> dict:
        # repeats 3 times to remove nested empty values
        if not self.minimize_json_output: return d
        if type(d) == list: return [self.cleanup_dict(v) for v in d]
        if type(d) != dict: return d
        return {
                k: self.cleanup_dict(v) if type(v) in [dict, list] else v 
                for k, v in d.items() 
                if v not in [0.0, 0, [], {}, "", None, "null"] and
                k not in ["x", "y", "width", "height"]
        }

    def download_profile(self, result: Metadata, username: str) -> Metadata:
        # download basic profile info
        url = result.get_url()
        user = self.call_api("v2/user/by/username", {"username": username}).get("user")
        assert user, f"User {username} not found"
        user = self.cleanup_dict(user)

        result.set_title(user.get("full_name", username)).set("data", user)
        if pic_url := user.get("profile_pic_url_hd", user.get("profile_pic_url")):
            filename = self.download_from_url(pic_url)
            result.add_media(Media(filename=filename), id=f"profile_picture")

        if self.full_profile:
            user_id = user.get("pk")
            # download all posts
            self.download_all_posts(result, user_id)

            # download all stories
            try:
                stories = self._download_stories_reusable(result, username)
                result.set("#stories", len(stories))
            except Exception as e:
                result.append("errors", f"Error downloading stories for {username}")
                logger.error(f"Error downloading stories for {username}: {e}")

            # download all highlights
            try:
                count_highlights = 0
                highlights = self.call_api(f"v1/user/highlights", {"user_id": user_id})
                for h in highlights:
                    try: 
                        h_info = self._download_highlights_reusable(result, h.get("pk"))
                        count_highlights += len(h_info.get("items", []))
                    except Exception as e:
                        result.append("errors", f"Error downloading highlight id{h.get('pk')} for {username}")
                        logger.error(f"Error downloading highlight id{h.get('pk')} for {username}: {e}")
                result.set("#highlights", count_highlights)
            except Exception as e:
                result.append("errors", f"Error downloading highlights for {username}")
                logger.error(f"Error downloading highlights for {username}: {e}")

        result.set_url(url) # reset as scrape_item modifies it
        return result.success("insta profile")

    def download_post(self, result: Metadata, code: str = None, id: str = None, context: str = None) -> Metadata:
        if id:
            post = self.call_api(f"v1/media/by/id", {"id": id})
        else:
            post = self.call_api(f"v1/media/by/code", {"code": code})
        assert post, f"Post {id or code} not found"

        if caption_text := post.get("caption_text"):
            result.set_title(caption_text)

        post = self.scrape_item(result, post, context)

        if post.get("taken_at"): result.set_timestamp(post.get("taken_at"))
        return result.success(f"insta {context or 'post'}")

    def download_highlights(self, result: Metadata, id: str) -> Metadata:
        h_info = self._download_highlights_reusable(result, id)
        items = len(h_info.get("items", []))
        del h_info["items"]
        result.set_title(h_info.get("title")).set("data", h_info).set("#reels", items)
        return result.success("insta highlights")
    
    def _download_highlights_reusable(self, result: Metadata, id: str) ->dict:
        full_h = self.call_api(f"v2/highlight/by/id", {"id": id})
        h_info = full_h.get("response", {}).get("reels", {}).get(f"highlight:{id}")
        assert h_info, f"Highlight {id} not found: {full_h=}"

        if cover_media := h_info.get("cover_media", {}).get("cropped_image_version", {}).get("url"):
            filename = self.download_from_url(cover_media)
            result.add_media(Media(filename=filename), id=f"cover_media highlight {id}")

        items = h_info.get("items", [])[::-1] # newest to oldest
        for h in tqdm(items, desc="downloading highlights", unit="highlight"):
            try: self.scrape_item(result, h, "highlight")
            except Exception as e:
                result.append("errors", f"Error downloading highlight {h.get('id')}")
                logger.error(f"Error downloading highlight, skipping {h.get('id')}: {e}")
        
        return h_info
  
    def download_stories(self, result: Metadata, username: str) -> Metadata:
        now = datetime.now().strftime("%Y-%m-%d_%H-%M")
        stories = self._download_stories_reusable(result, username)
        result.set_title(f"stories {username} at {now}").set("#stories", len(stories))
        return result.success(f"insta stories {now}")
    
    def _download_stories_reusable(self, result: Metadata, username: str) -> list[dict]:
        stories = self.call_api(f"v1/user/stories/by/username", {"username": username})
        assert stories, f"Stories for {username} not found"
        stories = stories[::-1] # newest to oldest

        for s in tqdm(stories, desc="downloading stories", unit="story"):
            try: self.scrape_item(result, s, "story")
            except Exception as e:
                result.append("errors", f"Error downloading story {s.get('id')}")
                logger.error(f"Error downloading story, skipping {s.get('id')}: {e}")
        return stories
        
    def download_all_posts(self, result: Metadata, user_id: str):
        end_cursor = None
        pbar = tqdm(desc="downloading posts")

        post_count = 0
        while end_cursor != "":
            posts = self.call_api(f"v1/user/medias/chunk", {"user_id": user_id, "end_cursor": end_cursor})
            if not len(posts): break
            posts, end_cursor = posts[0], posts[1]
            logger.info(f"parsing {len(posts)} posts, next {end_cursor=}")

            for p in posts:
                try: self.scrape_item(result, p, "post")
                except Exception as e:
                    result.append("errors", f"Error downloading post {p.get('id')}")
                    logger.error(f"Error downloading post, skipping {p.get('id')}: {e}")
                pbar.update(1)
                post_count+=1
        result.set("#posts", post_count)


### reusable parsing utils below

    def scrape_item(self, result:Metadata, item:dict, context:str=None) -> dict:
        """
        receives a Metadata and an API dict response
        fetches the media and adds it to the Metadata
        cleans and returns the API dict
        context can be used to give specific id prefixes to media
        """
        if "clips_metadata" in item:
            if reusable_text := item.get("clips_metadata", {}).get("reusable_text_attribute_string"):
                item["clips_metadata_text"] = reusable_text
            if self.minimize_json_output: 
                del item["clips_metadata"]

        if code := item.get("code"): 
            result.set("url", f"https://www.instagram.com/p/{code}/")
            
        resources = item.get("resources", [])
        item, media, media_id = self.scrape_media(item, context)
        # if resources are present take the main media from the first resource
        if not media and len(resources):
            _, media, media_id = self.scrape_media(resources[0], context)
            resources = resources[1:]
        
        assert media, f"Image/video not found in {item=}"
            
        # posts with multiple items contain a resources list
        resources_metadata = Metadata()
        for r in resources:
            self.scrape_item(resources_metadata, r)
        if not resources_metadata.is_empty():
            media.set("other media", resources_metadata.media)

        result.add_media(media, id=media_id)
        return item
    
    def scrape_media(self, item: dict, context:str) -> tuple[dict, Media, str]:
        # remove unnecessary info
        if self.minimize_json_output: 
            for k in ["image_versions", "video_versions", "video_dash_manifest"]:
                if k in item: del item[k]
        item = self.cleanup_dict(item)

        image_media = None
        if image_url := item.get("thumbnail_url"):
            filename = self.download_from_url(image_url, verbose=False)
            image_media = Media(filename=filename)
            
        # retrieve video info
        best_id = item.get('id', item.get('pk'))
        taken_at = item.get("taken_at")
        code = item.get("code")
        if video_url := item.get("video_url"):
            filename = self.download_from_url(video_url, verbose=False)
            video_media = Media(filename=filename)
            if taken_at: video_media.set("date", taken_at)
            if code: video_media.set("url", f"https://www.instagram.com/p/{code}")
            video_media.set("preview", [image_media])
            video_media.set("data", [item])
            return item, video_media, f"{context or 'video'} {best_id}"
        elif image_media:
            if taken_at: image_media.set("date", taken_at)
            if code: image_media.set("url", f"https://www.instagram.com/p/{code}")
            image_media.set("data", [item])
            return item, image_media, f"{context or 'image'} {best_id}"
        
        return item, None, None