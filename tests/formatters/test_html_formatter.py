import unittest

from auto_archiver.core.context import ArchivingContext
from auto_archiver.formatters.html_formatter import HtmlFormatter
from auto_archiver.core import Metadata, Media


class TestHTMLFormatter(unittest.TestCase):

    def setUp(self):
        ArchivingContext.prev_algorithm = ArchivingContext.get("hash_enricher.algorithm", "")
        ArchivingContext.set("hash_enricher.algorithm", "SHA-256")
        return super().setUp()
    
    def tearDown(self):
        ArchivingContext.set("hash_enricher.algorithm", ArchivingContext.prev_algorithm)
        del ArchivingContext.prev_algorithm
        return super().tearDown()

    def test_format(self):
        formatter = HtmlFormatter({})
        metadata = Metadata().set("content", "Hello, world!").set_url('https://example.com')

        final_media = formatter.format(metadata)
        self.assertIsInstance(final_media, Media)
        self.assertIn(".html", final_media.filename)
        with open (final_media.filename, "r") as f:
            content = f.read()
            self.assertIn("Hello, world!", content)
        self.assertEqual("text/html", final_media.mimetype)
        self.assertIn("SHA-256:", final_media.get('hash'))