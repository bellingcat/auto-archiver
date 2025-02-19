import pytest
from auto_archiver.core import Metadata, Media
from auto_archiver.modules.thumbnail_enricher import ThumbnailEnricher


@pytest.fixture
def thumbnail_enricher(setup_module, mock_binary_dependencies) -> ThumbnailEnricher:
    config: dict = {
        "thumbnails_per_minute": 60,
        "max_thumbnails": 4,
    }
    return setup_module("thumbnail_enricher", config)


@pytest.fixture
def metadata_with_video():
    m = Metadata()
    m.set_url("https://example.com")
    m.add_media(Media(filename="video.mp4").set("id", "video1"))
    return m


@pytest.fixture
def mock_ffmpeg_environment(mocker):
    # Mocking all the ffmpeg calls in one place
    mock_ffmpeg_input = mocker.patch("ffmpeg.input")
    mock_makedirs = mocker.patch("os.makedirs")
    mocker.patch.object(Media, "is_video", return_value=True),
    mock_probe = mocker.patch(
        "ffmpeg.probe",
        return_value={
            "streams": [
                {"codec_type": "video", "duration": "120"}
            ]  # Default 2-minute duration, but can override in tests
        },
    )
    mock_output = mocker.MagicMock()
    mock_ffmpeg_input.return_value.filter.return_value.output.return_value = (
        mock_output
    )

    return {
        "mock_ffmpeg_input": mock_ffmpeg_input,
        "mock_makedirs": mock_makedirs,
        "mock_output": mock_output,
        "mock_probe": mock_probe,
    }


@pytest.mark.parametrize("thumbnails_per_minute, max_thumbnails, expected_count", [
    (10, 5, 5),  # Capped at max_thumbnails
    (1, 10, 2),  # Less than max_thumbnails
    (60, 7, 7),  # Matches exactly
])
def test_enrich_thumbnail_limits(
    thumbnail_enricher, metadata_with_video, mock_ffmpeg_environment,
    thumbnails_per_minute, max_thumbnails, expected_count
):
    thumbnail_enricher.thumbnails_per_minute = thumbnails_per_minute
    thumbnail_enricher.max_thumbnails = max_thumbnails

    thumbnail_enricher.enrich(metadata_with_video)

    assert mock_ffmpeg_environment["mock_output"].run.call_count == expected_count
    thumbnails = metadata_with_video.media[0].get("thumbnails")
    assert len(thumbnails) == expected_count

def test_enrich_handles_probe_failure(thumbnail_enricher, metadata_with_video, mocker):

    mocker.patch("ffmpeg.probe", side_effect=Exception("Probe error"))
    mocker.patch("os.makedirs")
    mock_logger = mocker.patch("loguru.logger.error")
    mocker.patch.object(Media, "is_video", return_value=True)

    thumbnail_enricher.enrich(metadata_with_video)
    # Ensure error was logged
    mock_logger.assert_called_with(
        f"error getting duration of video video.mp4: Probe error"
    )
    # Ensure no thumbnails were created
    thumbnails = metadata_with_video.media[0].get("thumbnails")
    assert thumbnails is None


def test_enrich_skips_non_video_files(thumbnail_enricher, metadata_with_video, mocker):
        mocker.patch.object(Media, "is_video", return_value=False)
        mock_ffmpeg = mocker.patch("ffmpeg.input")
        thumbnail_enricher.enrich(metadata_with_video)
        mock_ffmpeg.assert_not_called()


@pytest.mark.parametrize("thumbnails_per_minute,max_thumbnails,expected_count", [
    (60, 5, 5), # caught by max
    (60, 20, 10), # caught by t/min
    (0, 20, 1), # test min caught (1)
    (11, 20, 1), # test min caught (1)
    (12, 20, 2), # test caught by t/min
])
def test_enrich_handles_short_video(
    thumbnail_enricher, metadata_with_video, mock_ffmpeg_environment, thumbnails_per_minute, max_thumbnails, expected_count, mocker
):
    # override mock duration
    fake_duration = 10
    mocker.patch(
        "ffmpeg.probe",
        return_value={ "streams": [{"codec_type": "video", "duration": str(fake_duration)}]},
    )
    thumbnail_enricher.thumbnails_per_minute = thumbnails_per_minute
    thumbnail_enricher.max_thumbnails = max_thumbnails

    thumbnail_enricher.enrich(metadata_with_video)
    assert mock_ffmpeg_environment["mock_output"].run.call_count == expected_count
    thumbnails = metadata_with_video.media[0].get("thumbnails")
    assert len(thumbnails) == expected_count


def test_uses_existing_duration(
    thumbnail_enricher, metadata_with_video, mock_ffmpeg_environment
):
    metadata_with_video.media[0].set("duration", 60)
    thumbnail_enricher.enrich(metadata_with_video)
    mock_ffmpeg_environment["mock_probe"].assert_not_called()
    assert mock_ffmpeg_environment["mock_output"].run.call_count == 4


def test_enrich_metadata_structure(thumbnail_enricher, metadata_with_video, mock_ffmpeg_environment, mocker):
    fake_duration = 120
    mocker.patch("ffmpeg.probe", return_value={'streams': [{'codec_type': 'video', 'duration': str(fake_duration)}]})
    thumbnail_enricher.thumbnails_per_minute = 2
    thumbnail_enricher.max_thumbnails = 4

    thumbnail_enricher.enrich(metadata_with_video)

    media_item = metadata_with_video.media[0]
    thumbnails = media_item.get("thumbnails")

    # Assert normal metadata
    assert media_item.get("id") == "video1"
    assert media_item.get("duration") == fake_duration
    # Evenly spaced timestamps
    expected_timestamps = ["24.000s", "48.000s", "72.000s", "96.000s"]
    assert thumbnails is not None
    assert len(thumbnails) == 4

    for index, thumbnail in enumerate(thumbnails):
        assert thumbnail.filename is not None
        assert thumbnail.properties.get("id") == f"thumbnail_{index}"
        assert thumbnail.properties.get("timestamp") == expected_timestamps[index]
