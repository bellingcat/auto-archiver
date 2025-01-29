from auto_archiver.core.extractor import Extractor
class ExampleModule(Extractor):
    def download(self, item):
        print("do something")