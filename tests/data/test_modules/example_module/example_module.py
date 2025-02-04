from auto_archiver.core import Extractor, Enricher, Feeder, Database, Storage, Formatter, Metadata

class ExampleModule(Extractor, Enricher, Feeder, Database, Storage, Formatter):
    def download(self, item):
        print("download")

    def __iter__(self):
        yield Metadata().set_url("https://example.com")

    
    def done(self, result):
        print("done")

    def enrich(self, to_enrich):
        print("enrich")

    def get_cdn_url(self, media):
        return "nice_url"
    
    def save(self, item):
        print("save")
    
    def uploadf(self, file, key, **kwargs):
        print("uploadf")

    
    def format(self, item):
        print("format")
