import json
from .UwaziRequest import UwaziRequest


class Thesauris:
    def __init__(self, uwazi_request: UwaziRequest):
        self.uwazi_request = uwazi_request

    def get(self, language: str):
        response = self.uwazi_request.request_adapter.get(url=f'{self.uwazi_request.url}/api/thesauris',
                                                              headers=self.uwazi_request.headers,
                                                              cookies={'connect.sid': self.uwazi_request.connect_sid,
                                                                       'locale': language})

        return json.loads(response.content.decode('utf-8'))['rows']

    def add_value(self, thesauri_name, thesauri_id, thesauri_values, language):
        data = {'_id': thesauri_id,
                'name': thesauri_name,
                'values': [{'label': x, 'id': thesauri_values[x]} for x in thesauri_values]}

        response = self.uwazi_request.request_adapter.post(url=f'{self.uwazi_request.url}/api/thesauris',
                                                           headers=self.uwazi_request.headers,
                                                           cookies={'connect.sid': self.uwazi_request.connect_sid,
                                                                    'locale': language},
                                                           data=json.dumps(data))

        return json.loads(response.content)
