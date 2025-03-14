import pytest
import hashlib

from opentimestamps.core.timestamp import Timestamp, DetachedTimestampFile
from opentimestamps.calendar import RemoteCalendar
from opentimestamps.core.notary import PendingAttestation, BitcoinBlockHeaderAttestation

from auto_archiver.core import Metadata, Media


# TODO: Remove once timestamping overhaul is merged
@pytest.fixture
def sample_media(tmp_path) -> Media:
    """Fixture creating a Media object with temporary source file"""
    src_file = tmp_path / "source.txt"
    src_file.write_text("test content")
    return Media(_key="subdir/test.txt", filename=str(src_file))


@pytest.fixture
def sample_file_path(tmp_path):
    tmp_file = tmp_path / "test.txt"
    tmp_file.write_text("This is a test file content for OpenTimestamps")
    return str(tmp_file)


@pytest.fixture
def detached_timestamp_file():
    """Create a simple detached timestamp file for testing"""
    file_hash = hashlib.sha256(b"Test content").digest()
    from opentimestamps.core.op import OpSHA256

    file_hash_op = OpSHA256()
    timestamp = Timestamp(file_hash)

    # Add a pending attestation
    pending = PendingAttestation("https://example.calendar.com")
    timestamp.attestations.add(pending)

    # Add a bitcoin attestation
    bitcoin = BitcoinBlockHeaderAttestation(783000)  # Some block height
    timestamp.attestations.add(bitcoin)

    return DetachedTimestampFile(file_hash_op, timestamp)


@pytest.fixture
def verified_timestamp_file():
    """Create a timestamp file with a Bitcoin attestation"""
    file_hash = hashlib.sha256(b"Verified content").digest()
    from opentimestamps.core.op import OpSHA256

    file_hash_op = OpSHA256()
    timestamp = Timestamp(file_hash)

    # Add only a Bitcoin attestation
    bitcoin = BitcoinBlockHeaderAttestation(783000)  # Some block height
    timestamp.attestations.add(bitcoin)

    return DetachedTimestampFile(file_hash_op, timestamp)


@pytest.fixture
def pending_timestamp_file():
    """Create a timestamp file with only pending attestations"""
    file_hash = hashlib.sha256(b"Pending content").digest()
    from opentimestamps.core.op import OpSHA256

    file_hash_op = OpSHA256()
    timestamp = Timestamp(file_hash)

    # Add only pending attestations
    pending1 = PendingAttestation("https://example1.calendar.com")
    pending2 = PendingAttestation("https://example2.calendar.com")
    timestamp.attestations.add(pending1)
    timestamp.attestations.add(pending2)

    return DetachedTimestampFile(file_hash_op, timestamp)


@pytest.mark.download
def test_download_tsr(setup_module, mocker):
    """Test submitting a hash to calendar servers"""
    # Mock the RemoteCalendar submit method
    mock_submit = mocker.patch.object(RemoteCalendar, "submit")
    test_timestamp = Timestamp(hashlib.sha256(b"test").digest())
    mock_submit.return_value = test_timestamp

    # Create a calendar
    calendar = RemoteCalendar("https://alice.btc.calendar.opentimestamps.org")

    # Test submission
    file_hash = hashlib.sha256(b"Test file content").digest()
    result = calendar.submit(file_hash)

    assert mock_submit.called
    assert isinstance(result, Timestamp)
    assert result == test_timestamp


def test_verify_timestamp(setup_module, detached_timestamp_file):
    """Test the verification of timestamp attestations"""
    ots = setup_module("opentimestamps_enricher")

    # Test verification
    verification_info = ots.verify_timestamp(detached_timestamp_file)

    # Check verification results
    assert verification_info["attestation_count"] == 2
    assert verification_info["verified"] is True
    assert len(verification_info["attestations"]) == 2

    # Check attestation types
    assertion_types = [a["status"] for a in verification_info["attestations"]]
    assert "pending" in assertion_types
    assert "confirmed" in assertion_types

    # Check Bitcoin attestation details
    bitcoin_attestation = next(a for a in verification_info["attestations"] if a["status"] == "confirmed")
    assert bitcoin_attestation["block_height"] == 783000


def test_verify_pending_only(setup_module, pending_timestamp_file):
    """Test verification of timestamps with only pending attestations"""
    ots = setup_module("opentimestamps_enricher")

    verification_info = ots.verify_timestamp(pending_timestamp_file)

    assert verification_info["attestation_count"] == 2
    assert verification_info["verified"] is False

    # All attestations should be of type "pending"
    assert all(a["status"] == "pending" for a in verification_info["attestations"])

    # Check URIs of pending attestations
    uris = [a["uri"] for a in verification_info["attestations"]]
    assert "https://example1.calendar.com" in uris
    assert "https://example2.calendar.com" in uris


def test_verify_bitcoin_completed(setup_module, verified_timestamp_file):
    """Test verification of timestamps with completed Bitcoin attestations"""

    ots = setup_module("opentimestamps_enricher")

    verification_info = ots.verify_timestamp(verified_timestamp_file)

    assert verification_info["attestation_count"] == 1
    assert verification_info["verified"] is True
    assert "pending" not in verification_info

    # Check that the attestation is a Bitcoin attestation
    attestation = verification_info["attestations"][0]
    assert attestation["status"] == "confirmed"
    assert attestation["block_height"] == 783000


def test_full_enriching(setup_module, sample_file_path, sample_media, mocker):
    """Test the complete enrichment process"""

    # Mock the calendar submission to avoid network requests
    mock_calendar = mocker.patch.object(RemoteCalendar, "submit")

    # Create a function that returns a new timestamp for each call
    def side_effect(digest):
        test_timestamp = Timestamp(digest)
        # Add a bitcoin attestation to the test timestamp
        bitcoin = BitcoinBlockHeaderAttestation(783000)
        test_timestamp.attestations.add(bitcoin)
        return test_timestamp

    mock_calendar.side_effect = side_effect

    ots = setup_module("opentimestamps_enricher")

    # Create test metadata with sample file
    metadata = Metadata().set_url("https://example.com")
    sample_media.filename = sample_file_path
    metadata.add_media(sample_media)

    # Run enrichment
    ots.enrich(metadata)

    # Verify results
    assert metadata.get("opentimestamped") is True
    assert metadata.get("opentimestamps_count") == 1

    # Check that we have one parent media item: the original
    assert len(metadata.media) == 1

    # Check that the original media was updated
    assert metadata.media[0].get("opentimestamps") is True

    # Check the timestamp file media is a child of the original
    assert len(metadata.media[0].get("opentimestamp_files")) == 1

    timestamp_media = metadata.media[0].get("opentimestamp_files")[0]

    assert timestamp_media.get("opentimestamps_version") is not None

    # Check verification results on the timestamp media
    assert timestamp_media.get("verified") is True
    assert timestamp_media.get("attestation_count") == 1


def test_full_enriching_one_calendar_error(
    setup_module, sample_file_path, sample_media, mocker, pending_timestamp_file
):
    """Test enrichment when one calendar server returns an error"""
    # Mock the calendar submission to raise an exception
    mock_calendar = mocker.patch.object(RemoteCalendar, "submit")

    test_timestamp = Timestamp(bytes.fromhex("583988e03646c26fa290c5c2408540a2f4e2aa9be087aa4546aefb531385b935"))
    # Add a bitcoin attestation to the test timestamp
    bitcoin = BitcoinBlockHeaderAttestation(783000)
    test_timestamp.attestations.add(bitcoin)

    mock_calendar.side_effect = [test_timestamp, Exception("Calendar server error")]

    ots = setup_module(
        "opentimestamps_enricher",
        {
            "calendar_urls": [
                "https://alice.btc.calendar.opentimestamps.org",
                "https://bob.btc.calendar.opentimestamps.org",
            ]
        },
    )

    # Create test metadata with sample file
    metadata = Metadata().set_url("https://example.com")
    sample_media.filename = sample_file_path
    metadata.add_media(sample_media)

    # Run enrichment (should complete despite calendar errors)
    ots.enrich(metadata)

    # Verify results
    assert metadata.get("opentimestamped") is True
    assert metadata.get("opentimestamps_count") == 1  # only alice worked, not bob


def test_full_enriching_calendar_error(setup_module, sample_file_path, sample_media, mocker):
    """Test enrichment when calendar servers return errors"""
    # Mock the calendar submission to raise an exception
    mock_calendar = mocker.patch.object(RemoteCalendar, "submit")
    mock_calendar.side_effect = Exception("Calendar server error")

    ots = setup_module("opentimestamps_enricher")

    # Create test metadata with sample file
    metadata = Metadata().set_url("https://example.com")
    sample_media.filename = sample_file_path
    metadata.add_media(sample_media)

    # Run enrichment (should complete despite calendar errors)
    ots.enrich(metadata)

    # Verify results
    assert metadata.get("opentimestamped") is False
    assert metadata.get("opentimestamps_count") is None


def test_no_files_to_stamp(setup_module):
    """Test enrichment with no files to timestamp"""
    ots = setup_module("opentimestamps_enricher")

    # Create empty metadata
    metadata = Metadata().set_url("https://example.com")

    # Run enrichment
    ots.enrich(metadata)

    # Verify no timestamping occurred
    assert metadata.get("opentimestamped") is None
    assert len(metadata.media) == 0
