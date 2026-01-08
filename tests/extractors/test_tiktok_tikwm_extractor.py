from datetime import datetime, timezone
import time
import pytest
import yt_dlp

from auto_archiver.modules.generic_extractor.generic_extractor import GenericExtractor
from auto_archiver.modules.generic_extractor.tiktok import Tiktok, TikTokIE

from .test_extractor_base import TestExtractorBase


@pytest.fixture(autouse=True)
def skip_ytdlp_own_methods(mocker):
    # mock this method, so that we skip the ytdlp download in these tests
    mocker.patch("auto_archiver.modules.generic_extractor.tiktok.Tiktok.skip_ytdlp_download", return_value=True)
    mocker.patch(
        "auto_archiver.modules.generic_extractor.generic_extractor.GenericExtractor.suitable_extractors",
        return_value=[e for e in yt_dlp.YoutubeDL()._ies.values() if e.IE_NAME == "TikTok"],
    )


@pytest.fixture
def mock_get(mocker):
    return mocker.patch("auto_archiver.modules.generic_extractor.tiktok.requests.get")


@pytest.fixture
def tiktok_dropin() -> Tiktok:
    return Tiktok()


class TestTiktokTikwmExtractor(TestExtractorBase):
    """
    Test suite for TestTiktokTikwmExtractor.
    """

    extractor_module = "generic_extractor"
    extractor: GenericExtractor

    config = {}

    VALID_EXAMPLE_URL = "https://www.tiktok.com/@example/video/1234"

    @pytest.mark.parametrize(
        "url, is_suitable",
        [
            ("https://bellingcat.com", False),
            ("https://youtube.com", False),
            ("https://tiktok.co/", False),
            ("https://tiktok.com/", False),
            ("https://www.tiktok.com/", False),
            ("https://api.cool.tiktok.com/", False),
            (VALID_EXAMPLE_URL, True),
            ("https://www.tiktok.com/@bbcnews/video/7478038212070411542", True),
            ("https://www.tiktok.com/@ggs68taiwan.official/video/7441821351142362375", True),
            ("https://www.tiktok.com/t/ZP8YQ8e5j/", True),
            ("https://vt.tiktok.com/ZSMTJeqRP/", True),
            ("https://tiktok.com/@user/photo/123?lang=en", True),
        ],
    )
    def test_is_suitable(self, url, is_suitable, tiktok_dropin):
        assert tiktok_dropin.suitable(url, TikTokIE()) == is_suitable

    def test_invalid_json_responses(self, mock_get, make_item, caplog):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.side_effect = ValueError
        with caplog.at_level("DEBUG"):
            assert self.extractor.download(make_item(self.VALID_EXAMPLE_URL)) is False
            mock_get.assert_called_once()
            mock_get.return_value.json.assert_called_once()
            # first message is just the 'Skipping using ytdlp to download files for TikTok' message
            assert "Failed to parse JSON response from tikwm.com" in caplog.text

        mock_get.return_value.json.side_effect = Exception
        with caplog.at_level("ERROR"):
            assert self.extractor.download(make_item(self.VALID_EXAMPLE_URL)) is False
            mock_get.assert_called()
            assert mock_get.call_count == 2
            assert mock_get.return_value.json.call_count == 2
            assert "Failed to parse JSON response from tikwm.com" in caplog.text

    @pytest.mark.parametrize(
        "response",
        [
            ({"msg": "failure"}),
            ({"msg": "success"}),
        ],
    )
    def test_unsuccessful_responses(self, mock_get, make_item, response, caplog):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = response
        with caplog.at_level("DEBUG"):
            assert self.extractor.download(make_item(self.VALID_EXAMPLE_URL)) is False
            mock_get.assert_called_once()
            mock_get.return_value.json.assert_called_once()
            assert "Unable to download with tikwm.com: " in caplog.text

    @pytest.mark.parametrize(
        "response,is_success",
        [
            ({"data": {"id": 123, "images": []}}, False),
            ({"data": {"wmplay": "url", "images": ["img1.jpg"]}}, True),
            ({"data": {"play": "url", "images": ["img1.jpg"]}}, True),
            ({"data": {"images": ["img1.jpg"]}}, True),
        ],
    )
    def test_correct_extraction(self, mock_get, make_item, response, is_success, mocker):
        data = {k: v for k, v in response.get("data", {}).items()}
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"msg": "success", **response}
        result = self.extractor.download(make_item(self.VALID_EXAMPLE_URL))
        total_media = len(data.get("images", [])) + (1 if data.get("wmplay", data.get("play")) else 0)
        if is_success:
            assert result.is_success()
            assert len(result.media) == total_media
        else:
            assert result is False
        mock_get.assert_called()
        assert mock_get.call_count == 1 + total_media
        mock_get.return_value.json.assert_called_once()

    def test_correct_data_extracted(self, mock_get, make_item):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "msg": "success",
            "data": {
                "wmplay": "url",
                "origin_cover": "cover.jpg",
                "title": "Title",
                "id": 123,
                "duration": 60,
                "create_time": 1736301699,
                "author": "Author",
                "other": "data",
            },
        }

        result = self.extractor.download(make_item(self.VALID_EXAMPLE_URL))
        assert result.is_success()
        assert len(result.media) == 2
        assert result.get_title() == "Title"
        assert result.get("author") == "Author"
        assert result.get("other") == "data"
        assert result.get("comments") is None
        assert result.get("api_data") == {"id": 123, "other": "data"}
        assert result.media[1].get("duration") == 60
        assert result.get("timestamp") == datetime.fromtimestamp(1736301699, tz=timezone.utc)

    @pytest.mark.download
    def test_download_video(self, make_item):
        url = "https://www.tiktok.com/@bbcnews/video/7478038212070411542"

        result = self.extractor.download(make_item(url))
        assert result.is_success()
        assert len(result.media) == 2
        assert (
            result.get_title()
            == "The A23a iceberg is one of the world's oldest and it's so big you can see it from space. #Iceberg  #A23a  #Antarctica  #Ice  #ClimateChange  #DavidAttenborough  #Ocean  #Sea  #SouthGeorgia  #BBCNews "
        )
        assert result.get("author").get("unique_id") == "bbcnews"
        assert result.get("api_data").get("id") == "7478038212070411542"
        assert result.media[1].get("duration") == 59
        assert result.get("timestamp") == datetime.fromtimestamp(1741122000, tz=timezone.utc)

    @pytest.mark.download
    def test_download_sensitive_video(self, make_item):
        url = "https://www.tiktok.com/@ggs68taiwan.official/video/7441821351142362375"
        # Required for rate limiting
        time.sleep(1.1)
        result = self.extractor.download(make_item(url))
        assert result.is_success()
        assert len(result.media) == 2
        assert result.get_title() == "Căng nhất lúc này #ggs68 #ggs68taiwan #taiwan #dailoan #tiktoknews"
        assert result.get("author").get("id") == "7197400619475649562"
        assert result.get("api_data").get("id") == "7441821351142362375"
        assert result.media[1].get("duration") == 34
        assert result.get("timestamp") == datetime.fromtimestamp(1732684060, tz=timezone.utc)
