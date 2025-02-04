import pytest

@pytest.fixture
def headerless_csv_file():
    return "tests/data/csv_no_headers.csv"

@pytest.fixture
def header_csv_file():
    return "tests/data/csv_with_headers.csv"

@pytest.fixture
def header_csv_file_non_default_column():
    return "tests/data/csv_with_headers_non_default_column.csv"


def test_csv_feeder_no_headers(headerless_csv_file, setup_module):
    from auto_archiver.modules.csv_feeder.csv_feeder import CSVFeeder

    feeder = setup_module(CSVFeeder, {"files": [headerless_csv_file]})

    urls = list(feeder)
    assert len(urls) == 2
    assert urls[0].get_url() == "https://example.com/1/"
    assert urls[1].get_url() == "https://example.com/2/"

def test_csv_feeder_with_headers(header_csv_file, setup_module):
    from auto_archiver.modules.csv_feeder.csv_feeder import CSVFeeder

    feeder = setup_module(CSVFeeder, {"files": [header_csv_file]})

    urls = list(feeder)
    assert len(urls) == 2
    assert urls[0].get_url() == "https://example.com/1/"
    assert urls[1].get_url() == "https://example.com/2/"

def test_csv_feeder_wrong_column(header_csv_file, setup_module, caplog):
    from auto_archiver.modules.csv_feeder.csv_feeder import CSVFeeder


    with caplog.at_level("WARNING"):
        feeder = setup_module(CSVFeeder, {"files": [header_csv_file], "column": 1})
        urls = list(feeder)

    assert len(urls) == 0
    assert "Not a valid URL in row" in caplog.text
    assert len(caplog.records) == 2


def test_csv_feeder_column_by_name(header_csv_file, setup_module):
    from auto_archiver.modules.csv_feeder.csv_feeder import CSVFeeder

    feeder = setup_module(CSVFeeder, {"files": [header_csv_file], "column": "webpages"})

    urls = list(feeder)
    assert len(urls) == 2
    assert urls[0].get_url() == "https://example.com/1/"
    assert urls[1].get_url() == "https://example.com/2/"