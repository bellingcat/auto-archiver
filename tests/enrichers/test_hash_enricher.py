from unittest import TestCase

from auto_archiver.enrichers.hash_enricher import HashEnricher
from auto_archiver.core import Metadata, Media

class TestHashEnricher(TestCase):
    def test_calculate_hash_sha256(self):
        # test SHA-256
        he = HashEnricher({"algorithm": "SHA-256", "chunksize": 1})
        assert he.calculate_hash("tests/data/testfile_1.txt") == "1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014"
        assert he.calculate_hash("tests/data/testfile_2.txt") == "60303ae22b998861bce3b28f33eec1be758a213c86c93c076dbe9f558c11c752"

    def test_calculate_hash_sha3_512(self):
        # test SHA3-512
        he = HashEnricher({"algorithm": "SHA3-512", "chunksize": 1})
        assert he.calculate_hash("tests/data/testfile_1.txt") == "d2d8cc4f369b340130bd2b29b8b54e918b7c260c3279176da9ccaa37c96eb71735fc97568e892dc6220bf4ae0d748edb46bd75622751556393be3f482e6f794e"
        assert he.calculate_hash("tests/data/testfile_2.txt") == "e35970edaa1e0d8af7d948491b2da0450a49fd9cc1e83c5db4c6f175f9550cf341f642f6be8cfb0bfa476e4258e5088c5ad549087bf02811132ac2fa22b734c6"

    def test_default_config_values(self):
        he = HashEnricher(config={})
        assert he.algorithm == "SHA-256"
        assert he.chunksize == 16000000
    
    def test_invalid_chunksize(self):
        with self.assertRaises(AssertionError):
            he = HashEnricher({"chunksize": "-100"})

    def test_invalid_algorithm(self):
        with self.assertRaises(AssertionError):
            HashEnricher({"algorithm": "SHA-123"})

    def test_config(self):
        # test default config
        c = HashEnricher.configs()
        assert c["algorithm"]["default"] == "SHA-256"
        assert c["chunksize"]["default"] == 16000000
        assert c["algorithm"]["choices"] == ["SHA-256", "SHA3-512"]
        assert c["algorithm"]["help"] == "hash algorithm to use"
        assert c["chunksize"]["help"] == "number of bytes to use when reading files in chunks (if this value is too large you will run out of RAM), default is 16MB"

    def test_hash_media(self):

        he = HashEnricher({"algorithm": "SHA-256", "chunksize": 1})

        # generate metadata with two test files
        m = Metadata().set_url("https://example.com")

        # noop - the metadata has no media. Shouldn't fail
        he.enrich(m)

        m.add_media(Media("tests/data/testfile_1.txt"))
        m.add_media(Media("tests/data/testfile_2.txt"))

        he.enrich(m)

        self.assertEqual(m.media[0].get("hash"), "SHA-256:1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014")
        self.assertEqual(m.media[1].get("hash"), "SHA-256:60303ae22b998861bce3b28f33eec1be758a213c86c93c076dbe9f558c11c752")