import json
from typing import Dict, List

from .UwaziRequest import UwaziRequest


class Entities:
    def __init__(self, uwazi_request: UwaziRequest):
        self.uwazi_request = uwazi_request

    def get_one(self, shared_id: str, language: str):
        response = self.uwazi_request.request_adapter.get(url=f'{self.uwazi_request.url}/api/entities',
                                                          headers=self.uwazi_request.headers,
                                                          cookies={'connect.sid': self.uwazi_request.connect_sid,
                                                                   'locale': language},
                                                          params={'sharedId': shared_id, 'omitRelationships': 'true'})

        if response.status_code != 200 or len(json.loads(response.text)['rows']) == 0:
            self.uwazi_request.graylog.error(f'Error getting entity {shared_id} {language}')
            raise InterruptedError(f'Error getting entity {shared_id} {language}')

        return json.loads(response.content.decode('utf-8'))['rows'][0]

    def get_id(self, shared_id: str, language: str):
        entity = self.get_one(shared_id, language)
        return entity['_id']

    def get_shared_ids(self, to_process_template: str, batch_size: int, unpublished: bool = True):
        params = {'_types': f'["{to_process_template}"]',
                  'types': f'["{to_process_template}"]',
                  'unpublished': 'true' if unpublished else 'false',
                  'limit': batch_size,
                  'order': 'desc',
                  'sort': 'creationDate'
                  }

        response = self.uwazi_request.request_adapter.get(f'{self.uwazi_request.url}/api/search',
                                                          headers=self.uwazi_request.headers,
                                                          params=params,
                                                          cookies={'connect.sid': self.uwazi_request.connect_sid,
                                                                   'locale': 'en'})

        if response.status_code != 200:
            raise InterruptedError(f'Error getting entities to update')

        return [json_entity['sharedId'] for json_entity in json.loads(response.text)['rows']]

    # DM copy of above with searchterm
    def get_shared_ids_search_by_case_id(self, to_process_template: str, batch_size: int, case_id: str, unpublished: bool = True):
        params = {'_types': f'["{to_process_template}"]',
                  'types': f'["{to_process_template}"]',
                  'unpublished': 'true' if unpublished else 'false',
                  'limit': batch_size,
                  'order': 'desc',
                  # DM
                   #   'searchTerm': 'GAZ088',
                  'searchTerm': case_id,
                  'sort': 'creationDate'
                  }

        response = self.uwazi_request.request_adapter.get(f'{self.uwazi_request.url}/api/search',
                                                          headers=self.uwazi_request.headers,
                                                          params=params,
                                                          cookies={'connect.sid': self.uwazi_request.connect_sid,
                                                                   'locale': 'en'})

        if response.status_code != 200:
            raise InterruptedError(f'Error getting entities to update')

        return [json_entity['sharedId'] for json_entity in json.loads(response.text)['rows']]

    # DM search.v2 
    # https://github.com/huridocs/uwazi/issues/6601
    def get_shared_ids_search_v2_by_case_id(self, to_process_template: str, case_id: str):

        # this works but is querying all templates eg CASES and if Content had a case_id it would query this too.
        # url_and_query = f'{self.uwazi_request.url}/api/v2/search?filter[metadata.case_id]="{case_id}"'

        # filter on the correct template too
        url_and_query = f'{self.uwazi_request.url}/api/v2/search?filter[metadata.case_id]="{case_id}"&filter[template]={to_process_template}'

        response = self.uwazi_request.request_adapter.get(url_and_query,
                                                          headers=self.uwazi_request.headers,
                                                          cookies={'connect.sid': self.uwazi_request.connect_sid,
                                                                   'locale': 'en'})
        if response.status_code != 200:
            raise InterruptedError(f'Error doing search v2')

        return [json_entity['sharedId'] for json_entity in json.loads(response.text)['data']]

    # DM search.v2 - Thesaurus / Dictionaries
    # https://github.com/huridocs/uwazi/issues/6601
    # def get_foo(self, to_process_template: str, case_id: str):
    # def get_foo(self):

    #     # this works but is querying all templates eg CASES and if Content had a case_id it would query this too.
    #     # url_and_query = f'{self.uwazi_request.url}/api/v2/search?filter[metadata.case_id]="{case_id}"'
    #     # url_and_query = f'{self.uwazi_request.url}/api/v2/search?filter[metadata.selectPropertyName]="Shooting"'
    #     url_and_query = f'{self.uwazi_request.url}/api/v2/search'

    #     # filter on the correct template too
    #     # url_and_query = f'{self.uwazi_request.url}/api/v2/search?filter[metadata.case_id]="{case_id}"&filter[template]={to_process_template}'

    #     response = self.uwazi_request.request_adapter.get(url_and_query,
    #                                                       headers=self.uwazi_request.headers,
    #                                                       cookies={'connect.sid': self.uwazi_request.connect_sid,
    #                                                                'locale': 'en'})
    #     if response.status_code != 200:
    #         raise InterruptedError(f'Error getting foo')

    #     return [json_entity['sharedId'] for json_entity in json.loads(response.text)['data']]

    # DM dictionary / thesauri
    def get_dictionary_element_id_by_dictionary_name_and_element_title(self, dictionary_name: str, dictionary_element: str):
        response = self.uwazi_request.request_adapter.get(f'{self.uwazi_request.url}/api/dictionaries',
                                                          headers=self.uwazi_request.headers,
                                                          cookies={'connect.sid': self.uwazi_request.connect_sid,
                                                                   'locale': 'en'})

        if response.status_code != 200:
            raise InterruptedError(f'Error getting dictionaries')

        # don't know how to filter the dictionaries in v2 or v1, so just find what I want.. it all seems to be returned
        foo = json.loads(response.text)['rows']
        _id = None
        for row in foo:
            # eg HARM_SOURCE
            if row["name"] == dictionary_name:
                _id = row["_id"]
                break
        
        if _id is None:
            logger.warning(f'Problem finding dictionary name {dictionary_name}')
            return None

        # now iterate over the values in that id looking for the text from spreadsheet eg Shooting
        dictionary_element_id =None
        should_continue = True
        for row in foo:
            # eg HARM_SOURCE
            if row["name"] == dictionary_name:
                for value in row["values"]:
                    if value['label'].lower() == dictionary_element.lower().strip():
                        dictionary_element_id = value['id']
                        should_continue = False
                        break
                        
                    if should_continue:
                        # maybe this is a group eg Religious or Spiritual group which has 3 elements under it: Mosque, Church and Cemetery
                        if 'values' in value:
                            for foo in value['values']:
                                if foo['label'].lower() == dictionary_element.lower().strip():
                                    dictionary_element_id = foo['id']
                                    should_continue = False
                                    break

            if should_continue == False: break

        if dictionary_element_id is None:
            logger.warning(f'Problem finding dictionary element {dictionary_element}')
            return None 

        return dictionary_element_id



    def get(self, template_id: str, batch_size: int, language: str = 'en', published: bool = False):
        params = {'types': f'["{template_id}"]',
                  'unpublished': 'false' if published else 'true',
                  'limit': batch_size
                  }

        response = self.uwazi_request.request_adapter.get(f'{self.uwazi_request.url}/api/search',
                                                          headers=self.uwazi_request.headers,
                                                          params=params,
                                                          cookies={'connect.sid': self.uwazi_request.connect_sid,
                                                                   'locale': language})

        if response.status_code != 200:
            raise InterruptedError(f'Error getting entities to update')

        return json.loads(response.text)['rows']

    def get_by_id(self, entity_id):
        response = self.uwazi_request.request_adapter.get(url=f'{self.uwazi_request.url}/api/entities',
                                                          headers=self.uwazi_request.headers,
                                                          cookies={'connect.sid': self.uwazi_request.connect_sid},
                                                          params={'_id': entity_id, 'omitRelationships': 'true'})

        if response.status_code != 200 or len(json.loads(response.text)['rows']) == 0:
            return None

        entity = json.loads(response.text)['rows'][0]
        return entity

    def upload(self, entity: Dict[str, any], language: str):
        upload_response = self.uwazi_request.request_adapter.post(url=f'{self.uwazi_request.url}/api/entities',
                                                                  headers=self.uwazi_request.headers,
                                                                  cookies={
                                                                      'connect.sid': self.uwazi_request.connect_sid,
                                                                      'locale': language},
                                                                  data=json.dumps(entity))

        if upload_response.status_code != 200:
            message = f'Error uploading entity {upload_response.status_code} {upload_response.text} {entity}'
            self.uwazi_request.graylog.error(message)
            # return
            # DM - doing a catch on the caller for Error...
            return message

        if '_id' in entity:
            self.uwazi_request.graylog.info(f'Entity uploaded {entity["_id"]}')
        shared_id = json.loads(upload_response.text)['sharedId']
        return shared_id

    def delete(self, share_id: str):
        response = self.uwazi_request.request_adapter.delete(f'{self.uwazi_request.url}/api/documents',
                                                             headers=self.uwazi_request.headers,
                                                             params={'sharedId': share_id},
                                                             cookies={'connect.sid': self.uwazi_request.connect_sid})

        if response.status_code != 200:
            print(f'Error ({response.status_code}) deleting entity {share_id}')
            self.uwazi_request.graylog.info(f'Error ({response.status_code}) deleting entity {share_id}')
            return

        print(f'Syncer: Entity deleted {share_id}')
        self.uwazi_request.graylog.info(f'Syncer: Entity deleted {share_id}')

    def publish_entities(self, shared_ids: List[str]):
        entity_new_values = dict()
        entity_new_values['ids'] = shared_ids
        entity_new_values['values'] = {'published': True}

        response = self.uwazi_request.request_adapter.post(url=f'{self.uwazi_request.url}/api/entities/multipleupdate',
                                                           headers=self.uwazi_request.headers,
                                                           cookies={'connect.sid': self.uwazi_request.connect_sid},
                                                           data=json.dumps(entity_new_values))
        if response.status_code != 200:
            print(f'Error ({response.status_code}) publishing entities {shared_ids}')
            self.uwazi_request.graylog.info(f'Error ({response.status_code}) publishing entities {shared_ids}')
            return

        print(f'Syncer: Entities published {shared_ids}')
        self.uwazi_request.graylog.info(f'Syncer: Entities published {shared_ids}')

    def delete_entities(self, shared_ids: List[str]):
        entity_new_values = dict()
        entity_new_values['sharedIds'] = shared_ids

        response = self.uwazi_request.request_adapter.post(url=f'{self.uwazi_request.url}/api/entities/bulkdelete',
                                                           headers=self.uwazi_request.headers,
                                                           cookies={'connect.sid': self.uwazi_request.connect_sid},
                                                           data=json.dumps(entity_new_values))
        if response.status_code != 200:
            print(f'Error ({response.status_code}) deleting entities {shared_ids}')
            self.uwazi_request.graylog.info(f'Error ({response.status_code}) deleting entities {shared_ids}')
            return

        print(f'Syncer: Entities deleted {shared_ids}')
        self.uwazi_request.graylog.info(f'Syncer: Entities deleted {shared_ids}')

