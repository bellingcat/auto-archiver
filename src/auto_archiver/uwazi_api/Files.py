import json
import os
from pathlib import Path
from typing import List
from requests.exceptions import RetryError

from .Entities import Entities
from .UwaziRequest import UwaziRequest


class Files:
    language_to_file_language = {'fr': 'fra', 'es': 'spa', 'en': 'eng', 'pt': 'prt', 'ar': 'arb'}

    def __init__(self, uwazi_request: UwaziRequest, entities: Entities):
        self.uwazi_request = uwazi_request
        self.entities = entities

    def get_document(self, shared_id: str, language: str):
        entity = self.entities.get_one(shared_id, language)
        if language not in Files.language_to_file_language:
            return None

        language_document = Files.language_to_file_language[language]

        file_names_list = list(
            filter(lambda x: 'language' in x and x['language'] == language_document, entity['documents']))

        if len(file_names_list) == 0:
            return None

        return self.get_document_by_file_name(file_names_list[0]["filename"])

    def get_document_by_file_name(self, file_name: str):
        document_response = self.uwazi_request.request_adapter.get(
            url=f'{self.uwazi_request.url}/api/files/{file_name}',
            headers=self.uwazi_request.headers,
            cookies={'connect.sid': self.uwazi_request.connect_sid})

        if document_response.status_code != 200:
            self.uwazi_request.graylog.info(f'No document found for {file_name}')
            print(f'No document found for {file_name}')
            return None

        return document_response.content

    def save_document_to_path(self, shared_id: str, languages: List[str], path: str):
        for language in languages:
            document_content = self.get_document(shared_id, language)
            file_id = str(hash(document_content))

            if not os.path.exists(path):
                os.makedirs(path)

            file_path_pdf = Path(f'{path}/{file_id}.pdf')
            file_path_pdf.write_bytes(document_content)

    def upload_file(self, pdf_file_path, share_id, language, title):
        try:
            with open(pdf_file_path, 'rb') as pdf_file:
                unicode_escape_title = title.encode('utf-8').decode('unicode-escape')
                response = self.uwazi_request.request_adapter.post(
                    url=f'{self.uwazi_request.url}/api/files/upload/document',
                    data={'entity': share_id},
                    files={
                        'file': (unicode_escape_title, pdf_file, 'application/pdf')},
                    cookies={'connect.sid': self.uwazi_request.connect_sid,
                             'locale': language},
                    headers={'X-Requested-With': 'XMLHttpRequest'})

                if 'prettyMessage' in json.loads(response.text).keys():
                    print(json.loads(response.text).keys())
                    print(json.loads(response.text)['prettyMessage'])
                    print(json.loads(response.text)['validations'])
                    print(json.loads(response.text)['error'])
                    return False

        except FileNotFoundError:
            self.uwazi_request.graylog.info(f'No pdf found {pdf_file_path}')
            print(f'No pdf found {pdf_file_path}')
            return False
        except:
            print(f'Uploading without response {share_id} {title} {pdf_file_path}')
            return False

        return True

    def upload_image(self, image_binary, title, entity_shared_id, language):
        try:
            response = self.uwazi_request.request_adapter.post(
                url=f'{self.uwazi_request.url}/api/files/upload/attachment',
                data={'entity': entity_shared_id},
                files={
                    'file': (title, image_binary, 'image/png')},
                cookies={'connect.sid': self.uwazi_request.connect_sid,
                         'locale': language},
                headers={'X-Requested-With': 'XMLHttpRequest'})

            if 'prettyMessage' in json.loads(response.text).keys():
                print(json.loads(response.text).keys())
                print(json.loads(response.text)['prettyMessage'])
                print(json.loads(response.text)['validations'])
                print(json.loads(response.text)['error'])
                return None
        except:
            print(f'Uploading without response {entity_shared_id} {language} {title}')
            return None

        return json.loads(response.text)

    def delete_file(self, id):
        params = (
            ('_id', id),
        )
        try:
            self.uwazi_request.request_adapter.delete(url=f'{self.uwazi_request.url}/api/files',
                                                      cookies={'connect.sid': self.uwazi_request.connect_sid},
                                                      params=params,
                                                      headers={'X-Requested-With': 'XMLHttpRequest'})
        except RetryError:
            return False

        return True

    def get_entity_language(self, language):
        if language == 'other':
            return 'en'

        languages = [x[0] for x in Files.language_to_file_language.items() if x[1] == language]

        if len(languages) == 0:
            return None

        return languages[0]
