import logging
from .request_retry import requests_retry_session


class UwaziRequest:
    def __init__(self, url: str, user: str, password: str):
        url = url if url[-1] != '/' else url[:-1]
        self.url = url
        self.user = user
        self.password = password
        self.request_adapter = requests_retry_session()
        self.headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/json',
        }
        self.graylog = logging.getLogger('graylog')
        self.connect_sid = self.get_connect_sid()

    def get_connect_sid(self):
        response = self.request_adapter.post(f'{self.url}/api/login',
                                             headers=self.headers,
                                             json={'username': self.user, 'password': self.password})

        self.graylog.info(f'Login into {self.url}: {response.status_code}')
        return response.cookies['connect.sid']