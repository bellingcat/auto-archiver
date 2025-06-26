import pytest
from PIL import UnidentifiedImageError

from auto_archiver.core import Metadata, Media
from auto_archiver.modules.pdq_hash_enricher import PdqHashEnricher


@pytest.fixture
def enricher(setup_module):
    return setup_module("pdq_hash_enricher", {})


@pytest.fixture
def metadata_with_images():
    m = Metadata()
    m.set_url("https://example.com")
    m.add_media(Media(filename="image1.jpg", _key="image1"))
    m.add_media(Media(filename="image2.jpg", _key="image2"))
    return m


def test_successful_enrich(metadata_with_images, mocker):
    mocker.patch("pdqhash.compute", return_value=([1, 0, 1, 0] * 64, 100))
    mocker.patch("PIL.Image.open")
    mocker.patch.object(Media, "is_image", return_value=True)
    enricher = PdqHashEnricher()
    enricher.enrich(metadata_with_images)

    # Ensure the hash is set for image media
    for media in metadata_with_images.media:
        assert media.get("pdq_hash") is not None


def test_enrich_skip_non_image(metadata_with_images, mocker):
    mocker.patch.object(Media, "is_image", return_value=False)
    mock_pdq = mocker.patch("pdqhash.compute")

    enricher = PdqHashEnricher()
    enricher.enrich(metadata_with_images)
    mock_pdq.assert_not_called()


def test_enrich_handles_corrupted_image(metadata_with_images, mocker):
    mocker.patch("PIL.Image.open", side_effect=UnidentifiedImageError("Corrupted image"))
    mock_pdq = mocker.patch("pdqhash.compute")
    mock_logger = mocker.patch("auto_archiver.utils.custom_logger.logger.error")
    enricher = PdqHashEnricher()
    enricher.enrich(metadata_with_images)

    assert mock_logger.call_count == len(metadata_with_images.media)
    mock_pdq.assert_not_called()


@pytest.mark.parametrize(
    "media_id, should_have_hash",
    [
        ("screenshot", False),
        ("warc-file-123", False),
        ("regular-image", True),
    ],
)
def test_enrich_excludes_by_filetype(media_id, should_have_hash, mocker):
    metadata = Metadata()
    metadata.set_url("https://example.com")
    metadata.add_media(Media(filename="image.jpg").set("id", media_id))

    mocker.patch("pdqhash.compute", return_value=([1, 0, 1, 0] * 64, 100))
    mocker.patch("PIL.Image.open")
    mocker.patch.object(Media, "is_image", return_value=True)

    enricher = PdqHashEnricher()
    enricher.enrich(metadata)

    media_item = metadata.media[0]
    assert (media_item.get("pdq_hash") is not None) == should_have_hash
