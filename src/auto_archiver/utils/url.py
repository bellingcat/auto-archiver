import re

class UrlUtil:
    telegram_private = re.compile(r"https:\/\/t\.me(\/c)\/(.+)\/(\d+)")
    is_istagram = re.compile(r"https:\/\/www\.instagram\.com")

    @staticmethod
    def clean(url): return url

    @staticmethod
    def is_auth_wall(url):
        """
        checks if URL is behind an authentication wall meaning steps like wayback, wacz, ... may not work
        """
        if UrlUtil.telegram_private.match(url): return True
        if UrlUtil.is_istagram.match(url): return True

        return False

