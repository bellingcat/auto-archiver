from .UwaziRequest import UwaziRequest


class CSV:
    def __init__(self, uwazi_request: UwaziRequest):
        self.uwazi_request = uwazi_request

    def upload(self, csv_name: str, template: str):
        csv_path = f'files/csv/{csv_name}.csv'

        with open(csv_path, 'rb') as file:
            response = self.uwazi_request.request_adapter.post(url=f'{self.uwazi_request.url}/api/import',
                                                               data={'template': template},
                                                               files={'content': ('content', file, 'application/csv')},
                                                               cookies={'connect.sid': self.uwazi_request.connect_sid},
                                                               headers={'X-Requested-With': 'XMLHttpRequest'})

            if response.status_code != 200:
                self.uwazi_request.graylog.info(f'Error uploading CSV', response)
                return

            print('CSV uploaded with status ', response.status_code)
            self.uwazi_request.graylog.info(f'CSV uploaded with status {response.status_code}')
