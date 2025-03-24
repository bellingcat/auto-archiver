from auto_archiver.modules.csv_db import CSVDb
from auto_archiver.core import Metadata


def test_store_item(tmp_path, setup_module):
    """Tests storing an item in the CSV database"""

    temp_db = tmp_path / "temp_db.csv"
    db = setup_module(CSVDb, {"csv_file": temp_db.as_posix()})

    item = (
        Metadata()
        .set_url("http://example.com")
        .set_title("Example")
        .set_content("Example content")
        .success("my-archiver")
    )

    db.done(item)

    with open(temp_db, "r", encoding="utf-8") as f:
        assert (
            f.read().strip()
            == f"status,metadata,media\nmy-archiver: success,\"{{'_processed_at': {repr(item.get('_processed_at'))}, 'url': 'http://example.com', 'title': 'Example', 'content': 'Example content'}}\",[]"
        )

    # TODO: csv db doesn't have a fetch method - need to add it (?)
    # assert db.fetch(item) == item
