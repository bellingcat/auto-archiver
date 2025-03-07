from datetime import datetime, timezone
import time
from unittest.mock import patch

import pytest

from auto_archiver.modules.tiktok_tikwm_extractor.tiktok_tikwm_extractor import TiktokTikwmExtractor
from .test_extractor_base import TestExtractorBase


class TestTiktokTikwmExtractor(TestExtractorBase):
    """
    Test suite for TestTiktokTikwmExtractor.
    """

    extractor_module = "tiktok_tikwm_extractor"
    extractor: TiktokTikwmExtractor

    config = {}

    @pytest.mark.parametrize("url,valid_url", [
        ("https://bellingcat.com", False),
        ("https://youtube.com", False),
        ("https://tiktok.co/", False),
        ("https://tiktok.com/", True),
        ("https://www.tiktok.com/", True),
        ("https://api.cool.tiktok.com/", True),
    ])
    @patch('auto_archiver.modules.tiktok_tikwm_extractor.tiktok_tikwm_extractor.logger')
    @patch('auto_archiver.modules.tiktok_tikwm_extractor.tiktok_tikwm_extractor.requests.get')
    def test_valid_urls(self, mock_get, mock_logger, make_item, url, valid_url):
        if valid_url:
            mock_get.return_value.status_code = 404
        assert self.extractor.download(make_item(url)) == False
        assert mock_get.call_count == int(valid_url)
        assert mock_logger.error.call_count == int(valid_url)

    @patch('auto_archiver.modules.tiktok_tikwm_extractor.tiktok_tikwm_extractor.logger')
    @patch('auto_archiver.modules.tiktok_tikwm_extractor.tiktok_tikwm_extractor.requests.get')
    def test_invalid_json_responses(self, mock_get, mock_logger, make_item):
        url = "https://tiktok.com/@user/123"
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.side_effect = ValueError
        assert self.extractor.download(make_item(url)) == False
        mock_get.assert_called_once()
        mock_get.return_value.json.assert_called_once()
        mock_logger.error.assert_called_once()
        assert mock_logger.error.call_args[0][0].startswith("failed to parse JSON response")

        mock_get.return_value.json.side_effect = Exception
        with pytest.raises(Exception):
            self.extractor.download(make_item(url))
        mock_get.assert_called()
        assert mock_get.call_count == 2
        assert mock_get.return_value.json.call_count == 2

    @pytest.mark.parametrize("response", [
        ({"msg": "failure"}),
        ({"msg": "success"}),
    ])
    @patch('auto_archiver.modules.tiktok_tikwm_extractor.tiktok_tikwm_extractor.logger')
    @patch('auto_archiver.modules.tiktok_tikwm_extractor.tiktok_tikwm_extractor.requests.get')
    def test_unsuccessful_responses(self, mock_get, mock_logger, make_item, response):
        url = "https://tiktok.com/@user/123"
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = response
        assert self.extractor.download(make_item(url)) == False
        mock_get.assert_called_once()
        mock_get.return_value.json.assert_called_once()
        mock_logger.error.assert_called_once()
        assert mock_logger.error.call_args[0][0].startswith("failed to get a valid response")

    @pytest.mark.parametrize("response,has_vid", [
        ({"data": {"id": 123}}, False),
        ({"data": {"wmplay": "url"}}, True),
        ({"data": {"play": "url"}}, True),
    ])
    @patch('auto_archiver.modules.tiktok_tikwm_extractor.tiktok_tikwm_extractor.logger')
    @patch('auto_archiver.modules.tiktok_tikwm_extractor.tiktok_tikwm_extractor.requests.get')
    def test_correct_extraction(self, mock_get, mock_logger, make_item, response, has_vid):
        url = "https://tiktok.com/@user/123"
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"msg": "success", **response}

        result = self.extractor.download(make_item(url))
        if not has_vid:
            assert result == False
        else:
            assert result.is_success()
            assert len(result.media) == 1
        mock_get.assert_called()
        assert mock_get.call_count == 1 + int(has_vid)
        mock_get.return_value.json.assert_called_once()
        if not has_vid:
            mock_logger.error.assert_called_once()
            assert mock_logger.error.call_args[0][0].startswith("no valid video URL found")
        else:
            mock_logger.error.assert_not_called()

    @patch('auto_archiver.modules.tiktok_tikwm_extractor.tiktok_tikwm_extractor.requests.get')
    def test_correct_extraction(self, mock_get, make_item):
        url = "https://tiktok.com/@user/123"
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"msg": "success", "data": {
            "wmplay": "url",
            "origin_cover": "cover.jpg",
            "title": "Title",
            "id": 123,
            "duration": 60,
            "create_time": 1736301699,
            "author": "Author",
            "other": "data"
        }}

        result = self.extractor.download(make_item(url))
        assert result.is_success()
        assert len(result.media) == 2
        assert result.get_title() == "Title"
        assert result.get("author") == "Author"
        assert result.get("api_data") == {"other": "data", "id": 123}
        # assert result.media[0].filename == "cover.jpg"
        # assert result.media[1].filename == "vid_123.mp4"
        assert result.media[1].get("duration") == 60
        assert result.get("timestamp") == datetime.fromtimestamp(1736301699, tz=timezone.utc)

    @pytest.mark.download
    def test_download_video(self, make_item):
        url = "https://www.tiktok.com/@bbcnews/video/7478038212070411542"

        result = self.extractor.download(make_item(url))
        assert result.is_success()
        assert len(result.media) == 2
        assert result.get_title() == "The A23a iceberg is one of the world's oldest and it's so big you can see it from space. #Iceberg  #A23a  #Antarctica  #Ice  #ClimateChange  #DavidAttenborough  #Ocean  #Sea  #SouthGeorgia  #BBCNews "
        assert result.get("author").get("unique_id") == "bbcnews"
        assert result.get("api_data").get("id") == '7478038212070411542'
        assert result.media[1].get("duration") == 59
        assert result.get("timestamp") == datetime.fromtimestamp(1741122000, tz=timezone.utc)

    @pytest.mark.download
    def test_download_sensitive_video(self, make_item, mock_sleep):
        # sleep is needed because of the rate limit
        mock_sleep.stop()
        time.sleep(1.1)
        mock_sleep.start()

        url = "https://www.tiktok.com/@ggs68taiwan.official/video/7441821351142362375"

        result = self.extractor.download(make_item(url))
        assert result.is_success()
        assert len(result.media) == 2
        assert result.get_title() == "Căng nhất lúc này #ggs68 #ggs68taiwan #taiwan #dailoan #tiktoknews"
        assert result.get("author").get("id") == "7197400619475649562"
        assert result.get("api_data").get("id") == '7441821351142362375'
        assert result.media[1].get("duration") == 34
        assert result.get("timestamp") == datetime.fromtimestamp(1732684060, tz=timezone.utc)
