import json
from .UwaziRequest import UwaziRequest


class Templates:
    def __init__(self, uwazi_request: UwaziRequest):
        self.uwazi_request = uwazi_request

    def set(self, language, template):
        response = self.uwazi_request.request_adapter.post(url=f'{self.uwazi_request.url}/api/templates',
                                                           headers=self.uwazi_request.headers,
                                                           cookies={'connect.sid': self.uwazi_request.connect_sid,
                                                                    'locale': language},
                                                           data=json.dumps(template))
        return json.loads(response.text)

    def get(self):
        response = self.uwazi_request.request_adapter.get(url=f'{self.uwazi_request.url}/api/templates',
                                                              headers=self.uwazi_request.headers,
                                                              cookies={'connect.sid': self.uwazi_request.connect_sid})

        return json.loads(response.text)['rows']
