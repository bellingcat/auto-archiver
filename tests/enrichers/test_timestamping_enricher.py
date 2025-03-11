import pytest
from auto_archiver.modules.timestamping_enricher.timestamping_enricher import TimestampingEnricher
from rfc3161_client import (
    TimestampRequestBuilder,
    TimeStampResponse,
    decode_timestamp_response,
)

from cryptography import x509

@pytest.fixture
def digicert():
    with open("tests/data/timestamp_token_digicert_com.crt", "rb") as f:
        return f.read()

@pytest.mark.download
def test_sign_data(setup_module):
    tsa_url = "http://timestamp.identrust.com"
    tsp: TimestampingEnricher = setup_module("timestamping_enricher")

    data = b"4b7b4e39f12b8c725e6e603e6d4422500316df94211070682ef10260ff5759ef"
    result: TimeStampResponse = tsp.sign_data(tsa_url, data)
    assert isinstance(result, TimeStampResponse)

    root_cert: x509.Certificate = tsp.verify_signed(result, data)
    assert root_cert.subject.rfc4514_string() == "CN=IdenTrust Commercial Root CA 1,O=IdenTrust,C=US"

    # test downloading the cert
    cert_chain = tsp.save_certificate(result)
    assert len(cert_chain) == 2

def test_tsp_enricher_download_syndication(setup_module, digicert):
    tsp: TimestampingEnricher = setup_module("timestamping_enricher")

    cert_chain = tsp.download_and_verify_certificate(digicert)
    assert len(cert_chain) == 3
    assert cert_chain[0].filename == f"{tsp.tmp_dir}/74515005589773707779.crt"
    assert cert_chain[1].filename == f"{tsp.tmp_dir}/95861100433808324400.crt"
    assert cert_chain[2].filename == f"{tsp.tmp_dir}/15527051335772373346.crt"


def test_tst_cert_valid(setup_module, digicert):
    tsp: TimestampingEnricher = setup_module("timestamping_enricher")
    
    try:
        tsp.verify_signed(digicert, b"4b7b4e39f12b8c725e6e603e6d4422500316df94211070682ef10260ff5759ef")
    except Exception as e:
        pytest.fail(f"Verification failed: {e}") 