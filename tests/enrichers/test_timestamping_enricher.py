import pytest
from auto_archiver.modules.timestamping_enricher.timestamping_enricher import TimestampingEnricher
from rfc3161_client import (
    TimeStampResponse,
    decode_timestamp_response,
)

from cryptography import x509

@pytest.fixture
def timestamp_response() -> TimeStampResponse:
    with open("tests/data/timestamping/timestamp_response.tsr", "rb") as f:
        return decode_timestamp_response(f.read())

@pytest.fixture
def wrong_order_timestamp_response() -> TimeStampResponse:
    with open("tests/data/timestamping/rfc3161-client-issue-104.tsr", "rb") as f:
        return decode_timestamp_response(f.read())


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

    verified_root_cert = tsp.verify_signed(timestamp_response, b"4b7b4e39f12b8c725e6e603e6d4422500316df94211070682ef10260ff5759ef")
    assert verified_root_cert.subject.rfc4514_string() == "CN=IdenTrust Commercial Root CA 1,O=IdenTrust,C=US"

    cert_chain = tsp.save_certificate(timestamp_response, verified_root_cert)
    assert len(cert_chain) == 3

    assert cert_chain[0].filename == f"{tsp.tmp_dir}/1 – 85078371663472981624.crt"
    assert cert_chain[1].filename == f"{tsp.tmp_dir}/2 – 85078758028491331763.crt"
    assert cert_chain[2].filename == f"{tsp.tmp_dir}/3 – 13298821034946342390.crt"


def test_order_crt_correctly(setup_module, wrong_order_timestamp_response):
    # reference: https://github.com/trailofbits/rfc3161-client/issues/104#issuecomment-2711244010
    tsp: TimestampingEnricher = setup_module("timestamping_enricher")

    # get the certificates, make sure the reordering is working:

    ordered_certs = tsp.tst_certs(wrong_order_timestamp_response)
    assert len(ordered_certs) == 2
    assert ordered_certs[0].subject.rfc4514_string() == "CN=TrustID Timestamping CA 3,O=IdenTrust,C=US"
    assert ordered_certs[1].subject.rfc4514_string() == "CN=TrustID Timestamp Authority,O=IdenTrust,C=US"


