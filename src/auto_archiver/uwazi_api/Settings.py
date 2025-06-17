import json
from .UwaziRequest import UwaziRequest


class Settings:
    def __init__(self, uwazi_request: UwaziRequest):
        self.uwazi_request = uwazi_request

    def get(self):
        response = self.uwazi_request.request_adapter.get(url=f'{self.uwazi_request.url}/api/settings',
                                                headers=self.uwazi_request.headers,
                                                cookies={'connect.sid': self.uwazi_request.connect_sid})

        return json.loads(response.text)

    def get_languages(self):
        uwazi_settings = self.get()
        return [x['key'] for x in uwazi_settings['languages']]