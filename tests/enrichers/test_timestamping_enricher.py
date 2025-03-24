from pathlib import Path
import pytest

from rfc3161_client import (
    TimeStampResponse,
    decode_timestamp_response,
)
import requests

from auto_archiver.modules.timestamping_enricher.timestamping_enricher import TimestampingEnricher
from auto_archiver.core import Metadata


@pytest.fixture
def timestamp_response() -> TimeStampResponse:
    with open("tests/data/timestamping/valid_timestamp.tsr", "rb") as f:
        return decode_timestamp_response(f.read())


@pytest.fixture
def wrong_order_timestamp_response() -> TimeStampResponse:
    with open("tests/data/timestamping/rfc3161-client-issue-104.tsr", "rb") as f:
        return decode_timestamp_response(f.read())


@pytest.fixture
def selfsigned_response() -> TimeStampResponse:
    with open("tests/data/timestamping/self_signed.tsr", "rb") as f:
        return decode_timestamp_response(f.read())


@pytest.fixture
def filehash():
    return "4b7b4e39f12b8c725e6e603e6d4422500316df94211070682ef10260ff5759ef"


@pytest.mark.download
def test_enriching(setup_module, sample_media):
    tsp: TimestampingEnricher = setup_module("timestamping_enricher")

    # tests the current TSAs set as default in the __manifest__ to make sure they are all still working

    # test the enrich method
    metadata = Metadata().set_url("https://example.com")
    sample_media.set("hash", "4b7b4e39f12b8c725e6e603e6d4422500316df94211070682ef10260ff5759ef")
    metadata.add_media(sample_media)
    tsp.enrich(metadata)


def test_full_enriching_selfsigned(setup_module, sample_media, mocker, selfsigned_response, filehash):
    mock_post = mocker.patch("requests.sessions.Session.post")
    mock_post.return_value.status_code = 200
    mock_decode_timestamp_response = mocker.patch(
        "auto_archiver.modules.timestamping_enricher.timestamping_enricher.decode_timestamp_response"
    )
    mock_decode_timestamp_response.return_value = selfsigned_response

    tsp: TimestampingEnricher = setup_module("timestamping_enricher", {"tsa_urls": ["http://timestamp.identrust.com"]})
    metadata = Metadata().set_url("https://example.com")
    sample_media.set("hash", filehash)
    metadata.add_media(sample_media)
    tsp.enrich(metadata)

    assert len(metadata.media) == 1  # doesn't allow self-signed

    # set self-signed on tsp
    tsp.allow_selfsigned = True

    tsp.enrich(metadata)

    assert len(metadata.media)


def test_full_enriching(setup_module, sample_media, mocker, timestamp_response, filehash):
    mock_post = mocker.patch("requests.sessions.Session.post")
    mock_post.return_value.status_code = 200
    mock_decode_timestamp_response = mocker.patch(
        "auto_archiver.modules.timestamping_enricher.timestamping_enricher.decode_timestamp_response"
    )
    mock_decode_timestamp_response.return_value = timestamp_response

    tsp: TimestampingEnricher = setup_module("timestamping_enricher", {"tsa_urls": ["http://timestamp.identrust.com"]})
    metadata = Metadata().set_url("https://example.com")
    sample_media.set("hash", filehash)
    metadata.add_media(sample_media)
    tsp.enrich(metadata)

    assert metadata.get("timestamped") is True
    assert len(metadata.media) == 2  # the original 'sample_media' and the new 'timestamp_media'

    timestamp_media = metadata.media[1]
    assert timestamp_media.filename == f"{tsp.tmp_dir}/hashes.txt"
    assert Path(timestamp_media.filename).read_text() == filehash

    # we only have one authority file because we only used one TSA
    assert len(timestamp_media.get("timestamp_authority_files")) == 1
    timestamp_authority_file = timestamp_media.get("timestamp_authority_files")[0]
    assert Path(timestamp_authority_file.filename).read_bytes() == timestamp_response.time_stamp_token()

    cert_chain = timestamp_authority_file.get("cert_chain")
    assert len(cert_chain) == 3
    assert cert_chain[0].filename == f"{tsp.tmp_dir}/1 – 85078758028491331763.crt"
    assert cert_chain[1].filename == f"{tsp.tmp_dir}/2 – 85078371663472981624.crt"
    assert cert_chain[2].filename == f"{tsp.tmp_dir}/3 – 13298821034946342390.crt"


def test_full_enriching_multiple_tsa(setup_module, sample_media, mocker, timestamp_response, filehash):
    mock_post = mocker.patch("requests.sessions.Session.post")
    mock_post.return_value.status_code = 200

    mock_decode_timestamp_response = mocker.patch(
        "auto_archiver.modules.timestamping_enricher.timestamping_enricher.decode_timestamp_response"
    )
    mock_decode_timestamp_response.return_value = timestamp_response

    tsp: TimestampingEnricher = setup_module(
        "timestamping_enricher", {"tsa_urls": ["http://example.com/timestamp1", "http://example.com/timestamp2"]}
    )
    metadata = Metadata().set_url("https://example.com")
    sample_media.set("hash", filehash)
    metadata.add_media(sample_media)
    tsp.enrich(metadata)

    assert metadata.get("timestamped") is True
    assert len(metadata.media) == 2  # the original 'sample_media' and the new 'timestamp_media'

    timestamp_media = metadata.media[1]
    assert len(timestamp_media.get("timestamp_authority_files")) == 2
    for timestamp_token_media in timestamp_media.get("timestamp_authority_files"):
        assert Path(timestamp_token_media.filename).read_bytes() == timestamp_response.time_stamp_token()
        assert len(timestamp_token_media.get("cert_chain")) == 3


@pytest.mark.download
def test_fails_for_digicert(setup_module):
    """
    Digicert TSRs are not compliant with RFC 3161.
    See https://github.com/trailofbits/rfc3161-client/issues/104#issuecomment-2621960840
    """
    tsa_url = "http://timestamp.digicert.com"
    tsp: TimestampingEnricher = setup_module("timestamping_enricher")

    data = b"4b7b4e39f12b8c725e6e603e6d4422500316df94211070682ef10260ff5759ef"
    with pytest.raises(ValueError) as e:
        tsp.sign_data(tsa_url, data)
    assert "ASN.1 parse error: ParseError" in str(e.value)


@pytest.mark.download
def test_download_tsr(setup_module):
    tsa_url = "http://timestamp.identrust.com"
    tsp: TimestampingEnricher = setup_module("timestamping_enricher")

    data = b"4b7b4e39f12b8c725e6e603e6d4422500316df94211070682ef10260ff5759ef"
    result: TimeStampResponse = tsp.sign_data(tsa_url, data)
    assert isinstance(result, TimeStampResponse)

    verified_root_cert = tsp.verify_signed(result, data)
    assert verified_root_cert.subject.rfc4514_string() == "CN=IdenTrust Commercial Root CA 1,O=IdenTrust,C=US"

    # test downloading the cert
    cert_chain = tsp.save_certificate(result, verified_root_cert)
    assert len(cert_chain) == 3


def test_verify_save(setup_module, timestamp_response):
    tsp: TimestampingEnricher = setup_module("timestamping_enricher")

    verified_root_cert = tsp.verify_signed(
        timestamp_response, b"4b7b4e39f12b8c725e6e603e6d4422500316df94211070682ef10260ff5759ef"
    )
    assert verified_root_cert.subject.rfc4514_string() == "CN=IdenTrust Commercial Root CA 1,O=IdenTrust,C=US"

    cert_chain = tsp.save_certificate(timestamp_response, verified_root_cert)
    assert len(cert_chain) == 3

    assert cert_chain[0].filename == f"{tsp.tmp_dir}/1 – 85078758028491331763.crt"
    assert cert_chain[1].filename == f"{tsp.tmp_dir}/2 – 85078371663472981624.crt"
    assert cert_chain[2].filename == f"{tsp.tmp_dir}/3 – 13298821034946342390.crt"


def test_order_crt_correctly(setup_module, wrong_order_timestamp_response):
    # reference: https://github.com/trailofbits/rfc3161-client/issues/104#issuecomment-2711244010
    tsp: TimestampingEnricher = setup_module("timestamping_enricher")

    # get the certificates, make sure the reordering is working:

    ordered_certs = tsp.tst_certs(wrong_order_timestamp_response)
    assert len(ordered_certs) == 2
    assert ordered_certs[0].subject.rfc4514_string() == "CN=TrustID Timestamp Authority,O=IdenTrust,C=US"
    assert ordered_certs[1].subject.rfc4514_string() == "CN=TrustID Timestamping CA 3,O=IdenTrust,C=US"


def test_invalid_tsa_404(setup_module, mocker):
    tsp = setup_module("timestamping_enricher")
    post_mock = mocker.patch("requests.sessions.Session.post")
    post_mock.side_effect = Exception("error")
    with pytest.raises(Exception, match="error"):
        tsp.sign_data("http://bellingcat.com/", b"my-message")


@pytest.mark.download
def test_invalid_tsa_invalid_response(setup_module, mocker):
    tsp = setup_module("timestamping_enricher")

    with pytest.raises(requests.exceptions.HTTPError, match="404 Client Error"):
        tsp.sign_data("http://bellingcat.com/page-not-found/", b"my-message")


def test_fail_on_selfsigned_cert(setup_module, selfsigned_response):
    tsp = setup_module("timestamping_enricher")
    root_cert = tsp.verify_signed(selfsigned_response, b"my-message")
    assert root_cert is None
