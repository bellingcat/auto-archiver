import tempfile
import os
import unittest

from auto_archiver.databases.csv_db import CSVDb
from auto_archiver.core import Metadata



class TestCSVdb(unittest.TestCase):

    def setUp(self):
        _, temp_db = tempfile.mkstemp(suffix="csv")
        self.temp_db = temp_db

    def tearDown(self):
        os.remove(self.temp_db)

    def test_store_item(self):
        db = CSVDb({
            "csv_db": {"csv_file": self.temp_db}
            })

        item = Metadata().set_url("http://example.com").set_title("Example").set_content("Example content").success("my-archiver")

        db.done(item)

        with open(self.temp_db, "r") as f:
            assert f.read().strip() == f"status,metadata,media\nmy-archiver: success,\"{{'_processed_at': {repr(item.get('_processed_at'))}, 'url': 'http://example.com', 'title': 'Example', 'content': 'Example content'}}\",[]"

        # TODO: csv db doesn't have a fetch method - need to add it (?)
        # assert db.fetch(item) == item