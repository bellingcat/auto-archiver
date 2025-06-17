# from uwazi_api.CSV import CSV
# from uwazi_api.Entities import Entities
# from uwazi_api.Files import Files
# from uwazi_api.Settings import Settings
# from uwazi_api.Templates import Templates
# from uwazi_api.Thesauris import Thesauris
# from uwazi_api.UwaziRequest import UwaziRequest
# from uwazi_api.iso_639_choices import iso_639_choices

from .CSV import CSV
from .Entities import Entities
from .Files import Files
from .Settings import Settings
from .Templates import Templates
from .Thesauris import Thesauris
from .UwaziRequest import UwaziRequest
from .iso_639_choices import iso_639_choices

class UwaziAdapter(object):
    def __init__(self, user, password, url):
        self.url = url
        self.sanitize_url()
        self.uwazi_request = UwaziRequest(self.url, user, password)
        self.entities = Entities(self.uwazi_request)
        self.files = Files(self.uwazi_request, self.entities)
        self.thesauris = Thesauris(self.uwazi_request)
        self.templates = Templates(self.uwazi_request)
        self.settings = Settings(self.uwazi_request)
        self.csv = CSV(self.uwazi_request)

    def sanitize_url(self):
        self.url = self.url if self.url[-1] != '/' else self.url[:-1]

        for language in iso_639_choices:
            if self.url[-3:] == f'/{language[0]}':
                self.url = self.url[:-3]
