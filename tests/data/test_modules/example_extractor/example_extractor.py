from auto_archiver.core import Extractor


class ExampleExtractor(Extractor):
    def download(self, item):
        print("download")
