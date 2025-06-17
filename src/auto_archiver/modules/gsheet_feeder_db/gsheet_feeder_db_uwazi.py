"""
GsheetsFeeder: A Google Sheets-based feeder for the Auto Archiver.

This reads data from Google Sheets and filters rows based on user-defined rules.
The filtered rows are processed into `Metadata` objects.

### Key properties
- validates the sheet's structure and filters rows based on input configurations.
- Ensures only rows with valid URLs and unprocessed statuses are included.
"""

from datetime import datetime, timezone
import os
import time
from typing import Tuple, Union
from urllib.parse import quote

import gspread
from loguru import logger
from slugify import slugify

from auto_archiver.core import Feeder, Database, Media
from auto_archiver.core import Metadata
from auto_archiver.modules.gsheet_feeder_db import GWorksheet
from auto_archiver.utils.misc import get_current_timestamp

from auto_archiver.uwazi_api.UwaziAdapter import UwaziAdapter

class GsheetsFeederDB(Feeder, Database):
    def setup(self) -> None:
        self.gsheets_client = gspread.service_account(filename=self.service_account)
        # TODO mv to validators
        if not self.sheet and not self.sheet_id:
            raise ValueError("You need to define either a 'sheet' name or a 'sheet_id' in your manifest.")

    def open_sheet(self):
        if self.sheet:
            return self.gsheets_client.open(self.sheet)
        else:  # self.sheet_id
            return self.gsheets_client.open_by_key(self.sheet_id)

    def __iter__(self) -> Metadata:
        # This is the 1.Feeder step ie opening the spreadsheet and iterating over the worksheets
        sh = self.open_sheet()

        # DM 10th Jun 25 - make sure Incidents worksheet is enumerated first if exists
        # This is for Uwazi integration
        def custom_sort(wks):
            # Prioritise 'Incidents' by giving it a lower sort value
            return (0 if wks.title == 'Incidents' else 1, wks.title)

        sorted_worksheets = sorted(sh.worksheets(), key=custom_sort)
        
        for ii, worksheet in enumerate(sorted_worksheets):
            
            if not self.should_process_sheet(worksheet.title):
                logger.debug(f"SKIPPED worksheet '{worksheet.title}' due to allow/block rules")
                continue
            logger.info(f"Opening worksheet {ii=}: {worksheet.title=} header={self.header}")
            gw = GWorksheet(worksheet, header_row=self.header, columns=self.columns)

            # DM 10th Jun 25 - Uwazi part 1 special case to process the Incidents tab
            if self.uwazi_integration == True and worksheet.title == "Incidents":
               logger.debug("Found uwazi integration Incidents (CASES) tab to process - doing this first before Sheet1")
               self._process_uwazi_incidents_tab(gw)
               # don't do the normal processing and yield metadata for Uwazi Incidents tab
               continue
           
            if len(missing_cols := self.missing_required_columns(gw)):
                logger.warning(
                    f"SKIPPED worksheet '{worksheet.title}' due to missing required column(s) for {missing_cols}"
                )
                continue

            # process and yield metadata here:
            yield from self._process_rows(gw)
            logger.info(f"Finished worksheet {worksheet.title}")

    # DM 10th Jun 25 
    def _process_uwazi_incidents_tab(self, gw: GWorksheet):
        logger.info(f"Processing Uwazi Incidents tab {gw.wks.title}")
        # New CASES (maybe an Incident)
        # reading from Incidents tab only
        for row in range(1 + self.header, gw.count_rows() + 1):
            try:
                url = gw.get_cell(row, 'icase_id').strip()
            except Exception as e:
                logger.error('Cant find case_id column in Incidents tab')
                raise
            # has to have a case_id ie not blank rows
            if not len(url): continue

            # logger.info(f" row {row} with url {url}")

            iimport_to_uwazi = gw.get_cell(row, 'iimport_to_uwazi')
            if iimport_to_uwazi == 'y': pass
            else:
                # logger.debug('Skipping incident as not y in import_to_uwazi')
                continue

            idate_imported_to_uwazi = gw.get_cell(row, 'idate_imported_to_uwazi').strip()
            if idate_imported_to_uwazi == "": pass
            else:
                # logger.debug('Incident already imported to Uwazi')
                continue

            # In Incident tab
            # There is a case_id, which has y in import_to_uwazi and no date_imported_to_uwazi is set

            import_to_uwazi_notes = ''

            ititle = gw.get_cell(row, 'ititle')
            icase_id = gw.get_cell(row, 'icase_id')

            logger.info(f'Importing {icase_id} {ititle}')

            idescription = gw.get_cell(row, 'idescription')
            ineighbourhood = gw.get_cell(row, 'ineighbourhood')

            # Date_Reported now called DATE_PRIMA_FACIE in the spreadsheet - 10th Jun 2025
            idate_reported = gw.get_cell(row, 'idate_reported')
            idate_reported_unix = 0
            if idate_reported == "": pass
            else:
                try:
                    datetime_obj = datetime.fromisoformat(idate_reported)
                    idate_reported_unix = datetime_obj.replace(tzinfo=timezone.utc).timestamp()
                except Exception as e:
                    message = f'Unknown idate_reported timestamp conversion from iso. '
                    logger.warning(message)
                    import_to_uwazi_notes = message
            
            # Date_Accessed
            idate_assessed = gw.get_cell(row, 'idate_assessed')
            idate_assessed_unix = 0
            if idate_assessed == "": pass
            else:
                try:
                    datetime_obj = datetime.fromisoformat(idate_assessed)
                    idate_assessed_unix = datetime_obj.replace(tzinfo=timezone.utc).timestamp()
                except:
                    message = 'Unknown idate_assessed timestamp converstion from iso. '
                    logger.warning(message)
                    import_to_uwazi_notes += message

            uwazi_adapter = UwaziAdapter(user=self.uwazi_user, password=self.uwazi_password, url=self.uwazi_url) 

            # HARM_SOURCE - single select
            harm_source_from_spreadsheet = gw.get_cell(row, 'iharm_source')
            harm_source_dictionary_element_id = None
            if harm_source_from_spreadsheet == '': 
                logger.debug("no harm source from spreadsheet")
            else:
                harm_source_dictionary_element_id = uwazi_adapter.entities.get_dictionary_element_id_by_dictionary_name_and_element_title("HARM_SOURCE", harm_source_from_spreadsheet)

                if harm_source_dictionary_element_id is None:
                    message = f"Dictionary element in HARM_SOURCE not found: {harm_source_from_spreadsheet}. "
                    logger.warning(message)
                    import_to_uwazi_notes += message

            # OBJECT_AFFECTED - multi select with groups in the thesauri/dictionary
            object_affected_from_spreadsheet = gw.get_cell(row, 'iobject_affected')
            objects = object_affected_from_spreadsheet.split(',')

            object_affected_list = []
            if objects == ['']:
                logger.debug('no object_affected from spreadsheet')
            else:
                for o in objects:
                    # what if Medical is passed which is a group name - business rule.. don't do this.
                    # need to pass all the element names explicitly if want them all
                            
                    object_affected_dictionary_element_id  = uwazi_adapter.entities.get_dictionary_element_id_by_dictionary_name_and_element_title("OBJECT_AFFECTED", o)
                    if object_affected_dictionary_element_id is None:
                        message = f'Couldnt find {o} in dictionary for OBJECT AFFECTED so not appending. '
                        logger.debug(message)
                        import_to_uwazi_notes += message
                    else:
                        object_affected_list.append(object_affected_dictionary_element_id)
            # create json list to send
            object_affected_result_list = []
            for oa in object_affected_list:
                # Create a new dictionary with the current value
                new_dict = {"value": oa}
                object_affected_result_list.append(new_dict)


            # PEOPLE_HARMED - multi select but no groups 
            people_harmed_from_spreadsheet = gw.get_cell(row, 'ipeople_harmed')
            objects = people_harmed_from_spreadsheet.split(',')

            people_harmed_list = []

            if objects == ['']:
                logger.debug('no people_harmed from spreadsheet')
            else:
                for o in objects:
                    people_harmed_dictionary_element_id  = uwazi_adapter.entities.get_dictionary_element_id_by_dictionary_name_and_element_title("PEOPLE_HARMED", o)
                    if people_harmed_dictionary_element_id is None:
                        message = f'Couldnt find {o} in dictionary for PEOPLE_HARMED so not appending. '
                        logger.debug(message)
                        import_to_uwazi_notes += message
                    else:
                        people_harmed_list.append(people_harmed_dictionary_element_id)

            # create json list to send
            people_harmed_result_list = []
            for ph in people_harmed_list:
                # Create a new dictionary with the current value
                new_dict = {"value": ph}
                people_harmed_result_list.append(new_dict)

                
            # GOVERNORATE - single select
            governorate_from_spreadsheet = gw.get_cell(row, 'igovernorate')
            governorate_dictionary_element_id = None
            if governorate_from_spreadsheet == '': 
                logger.debug("no governorate from spreadsheet")
            else:
                governorate_dictionary_element_id = uwazi_adapter.entities.get_dictionary_element_id_by_dictionary_name_and_element_title("GOVERNORATE", governorate_from_spreadsheet)

                if governorate_dictionary_element_id is None:
                    message = f"Dictionary element in GOVERNORATE not found: {governorate_from_spreadsheet}. "
                    logger.warning(message)
                    import_to_uwazi_notes += message

                        
            # CAMP - single select
            camp_from_spreadsheet = gw.get_cell(row, 'icamp')

            camp_dictionary_element_id = None
            if camp_from_spreadsheet == '': 
                logger.debug("no camp from spreadsheet")
            else:
                camp_dictionary_element_id = uwazi_adapter.entities.get_dictionary_element_id_by_dictionary_name_and_element_title("CAMP", camp_from_spreadsheet)

                if camp_dictionary_element_id is None:
                    message = f"Dictionary element in CAMP not found: {camp_from_spreadsheet}. "
                    logger.warning(message)
                    import_to_uwazi_notes += message

            # GEOLOCATION with comma or pipe
            igeolocation = gw.get_cell(row, 'igeolocation').strip()
            if igeolocation != "":
                try:
                    if "," in igeolocation:
                        parts = igeolocation.split(",", 1)
                    elif "|" in igeolocation:
                        parts = igeolocation.split("|", 1) 

                    lat = float(parts[0].strip())
                    long = float(parts[1].strip())
                    geolocation = [{
                        "value": {
                            "lat": lat,
                            "lon": long,
                            "label": ""
                        }
                    }]
                except:
                    message = f"Geolocation failed to parse {igeolocation}. "
                    logger.warning(message)
                    import_to_uwazi_notes += message
                    geolocation = []
            else: 
                geolocation = []

            # CASE_NATURE - single select
            case_nature_from_spreadsheet = gw.get_cell(row, 'icase_nature').strip()    
            case_nature_dictionary_element_id = None
            if case_nature_from_spreadsheet == '': 
                logger.debug("no case_nature from spreadsheet")
            else:
                case_nature_dictionary_element_id = uwazi_adapter.entities.get_dictionary_element_id_by_dictionary_name_and_element_title("CASE_NATURE", case_nature_from_spreadsheet)

                if case_nature_dictionary_element_id is None:
                    message = f"Dictionary element in CASE_NATURE not found in Uwazi: {case_nature_from_spreadsheet}. "
                    logger.warning(message)
                    import_to_uwazi_notes += message

                    
            # Create a new CASE
            case_entity = {
                'title': ititle,
                'template': self.uwazi_case_template_id, 
                "documents": [],
                "metadata": {
                    "generated_id": [ { "value": icase_id} ],
                    "image": [ { "value": "" } ],
                    "case_id": [ { "value": icase_id } ],
                    "description": [ { "value": idescription } ],
                    "neighbourhood": [ { "value": ineighbourhood } ],
                    "date_reported": [ { "value": idate_reported_unix } ],
                    "date_assessed": [ { "value": idate_assessed_unix } ],
                    "harm_source": [ { "value": harm_source_dictionary_element_id } ],
                    "object_affected": object_affected_result_list,
                    "people_harmed": people_harmed_result_list,
                    "governorate": [ { "value": governorate_dictionary_element_id } ],
                    "camp": [ { "value": camp_dictionary_element_id } ],
                    "case_nature": [ { "value": case_nature_dictionary_element_id } ],
                    "geolocation_geolocation": geolocation
                    }
                }

            # uwazi_adapter = UwaziAdapter(user=self.uwazi_user, password=self.uwazi_password, url=self.uwazi_url) 
            case_shared_id = uwazi_adapter.entities.upload(entity=case_entity, language='en')
            if case_shared_id.startswith('Error'):
                # case_shared_id contains the error message - look in Entities upload.
                message = f"{icase_id}  - {case_shared_id}"
                logger.warning(message)
                import_to_uwazi_notes += message
            else: 
                logger.success(f'Sent new CASE to Uwazi - {ititle}')

            gw.set_cell(row, 'idate_imported_to_uwazi',datetime.utcnow().replace(tzinfo=timezone.utc).isoformat())

            if import_to_uwazi_notes == '': import_to_uwazi_notes = "success"
            gw.set_cell(row, 'iimport_to_uwazi_notes', import_to_uwazi_notes)

            
            
    

    def _process_rows(self, gw: GWorksheet):
        for row in range(1 + self.header, gw.count_rows() + 1):
            url = gw.get_cell(row, "url").strip()
            if not len(url):
                continue
            original_status = gw.get_cell(row, "status")

            # DM 10th Jun 25 - Uwazi Part 2 - send Sheet1 data to Uwazi 
            # TODO use AI to help abstract this out with proper control flow

            if self.uwazi_integration == True:
                # we're using keep_going rather than continue as the normal archiver run 
                # will go through this code too for Glan and needs to keep on going

                keep_going = True
                # has the archiver already been run?
                if original_status == '':
                    logger.debug('Archiver not been run for the first time on this link')
                    keep_going = False

                # check uwazi column exists
                if keep_going:
                    try:
                        _ = gw.col_exists('import_to_uwazi')
                    except: 
                        keep_going = False
                        logger.error('Uwazi feature is on but import_to_uwazi column not present')
                        continue # to next row. 

                # is import_to_uwazi column 'y'
                if keep_going:
                    stu = gw.get_cell(row, 'import_to_uwazi').lower()
                    if stu == 'y':
                        pass
                    else:
                        keep_going = False

                # have we already sent it to uwazi?
                if keep_going:
                    di = gw.get_cell(row, 'date_imported_to_uwazi').lower()
                    if di == '':
                        pass
                    else:
                        # logger.debug('already imported to uwazi so ignore')
                        keep_going = False

                # assume that user only presses y to uwazi if a successful archive has taken place
                if keep_going:
                    import_to_uwazi_notes = ''

                    entry_number = gw.get_cell(row, 'folder')

                    logger.debug(f'Getting ready to make a Content item entry number: {entry_number} to send to Uwazi!')

                    uwazi_title = gw.get_cell(row, 'uwazi_title')
                    if uwazi_title == '':
                        uwazi_title = entry_number

                    link = gw.get_cell(row, 'url')

                    image_url1= gw.get_cell(row, 'image_url1')
                    image_url2= gw.get_cell(row, 'image_url2')
                    image_url3= gw.get_cell(row, 'image_url3')
                    image_url4= gw.get_cell(row, 'image_url4')

                    video_url1= gw.get_cell(row, 'video_url1')
                    video_url2= gw.get_cell(row, 'video_url2')

                    # Date Posted - make it Upload Timestamp (of the original image eg Twitter)
                    # it may be blank
                    # eg '2022-05-11T10:51:35+00:00'
                    upload_timestamp = gw.get_cell(row, 'timestamp')

                    # Convert the string to a datetime object
                    # it can be that it is blank (not sure why)
                    unix_timestamp = 0
                    if upload_timestamp == "":
                        pass
                    else:
                        try:
                            datetime_obj = datetime.fromisoformat(upload_timestamp)
                            unix_timestamp = datetime_obj.replace(tzinfo=timezone.utc).timestamp()
                        except:
                            message = 'unknown dateposted timestamp converstion from iso.'
                            logger.warning(message)
                            import_to_uwazi_notes += message

                    # a description
                    upload_title = gw.get_cell(row, 'title')

                    hash = gw.get_cell(row, 'hash')

                    # digital ocean link
                    archive_location = gw.get_cell(row, 'archive_location')

                    # geolocation_geolocation
                    geolocation = gw.get_cell(row, 'geolocation_geolocation')

                    if geolocation == "case" or geolocation == "CASE": 
                        # handle further down as need to copy from the case
                        pass
                    elif geolocation == "":
                        # do nothing and leave blank
                            geolocation_geolocation = []
                    else:
                        try:
                            if "," in geolocation:
                                parts = geolocation.split(",", 1)
                            elif "|" in geolocation:
                                parts = geolocation.split("|", 1) 

                            lat = float(parts[0].strip())
                            long = float(parts[1].strip())
                            geolocation_geolocation = [{
                                "value": {
                                    "lat": lat,
                                    "lon": long,
                                    "label": ""
                                }
                            }]
                        except:
                            message = f"geolocation failed to parse {parts}"
                            logger.warning(message)
                            import_to_uwazi_notes +=  message
                            geolocation_geolocation = []

                    # need to figure out the CASE entity value
                    # get it from the spreadsheet CASE
                    # eg GAZ088
                    case_id = gw.get_cell(row, 'case_id')

                    # DM 10th Jun 25 - new feature - what if we can have a blank CASE_ID then just upload the content without the link to the case.
                    # if len(case_id) == 0:
                    #     message = 'NOT IMPORTED - CASE_ID not found in spreadsheet - not imported into Uwazi as each Content template entity should have a CASE'
                    #     logger.warning(message)
                    #     import_to_uwazi_notes += message
                    #     gw.set_cell(row, 'import_to_uwazi_notes', import_to_uwazi_notes)
                    #     # set date_imported as otherwise it will try every run to import
                    #     gw.set_cell(row, 'date_imported_to_uwazi',datetime.utcnow().replace(tzinfo=timezone.utc).isoformat())
                    #     continue

                    description = gw.get_cell(row, 'description')

                    screenshot = gw.get_cell(row, 'screenshot')

                    # Does this CASE exist in Uwazi already?
                    uwazi_adapter = UwaziAdapter(user=self.uwazi_user, password=self.uwazi_password, url=self.uwazi_url) 

                    fooxx = uwazi_adapter.entities.get_shared_ids_search_v2_by_case_id(self.uwazi_case_template_id, case_id)

                    case_id_mongo = ''
                    # DM 11th Jun - no caseid is fine.
                    if len(fooxx) == 0: pass
                    #     message = 'NOT IMPORTED as CASE not found - problem. It should have been created in Uwazi before'
                    #     logger.warning(message)
                    #     import_to_uwazi_notes += message
                    #     gw.set_cell(row, 'import_to_uwazi_notes', import_to_uwazi_notes)
                    #     # set date_imported as otherwise it will try every run to import
                    #     gw.set_cell(row, 'date_imported_to_uwazi',datetime.utcnow().replace(tzinfo=timezone.utc).isoformat())
                    #     continue
                    else:
                        # There were CASES found in the search
                        # if the search for GAZ088 came back with multiple CASES we would be in trouble
                        if len(fooxx) > 1:
                            # This should never happen but it might if there are multiples cases in Uwazi
                            message = f'Search term {case_id} found multiple CASES in Uwazi - duplicates in Uwazi? Have taken the last one in search results'
                            logger.warning(message)
                            import_to_uwazi_notes += message
                            # take the last one as it was probably the one we're after
                            case_id_mongo = fooxx[-1]
                        else:
                            case_id_mongo = fooxx[0]

                    # only if actively set to 'case' in the content spreadsheet should we copy from CASE
                    # get the geolocation of this CASE and copy it onto the new Content entity we are making
                    # if there isn't a geolocation there already
                    if geolocation == 'case' or geolocation == "CASE":
                        try:
                                ggg = uwazi_adapter.entities.get_one(case_id_mongo, "en")
                                case_geoloc_from_uwazi_json = ggg['metadata']['geolocation_geolocation'][0]['value']
                                lat = case_geoloc_from_uwazi_json['lat']
                                lon = case_geoloc_from_uwazi_json['lon']
                                geolocation_geolocation = [{
                                    "value": {
                                        "lat": lat,
                                        "lon": lon,
                                        "label": ""
                                    }
                                }]
                        except:
                                logger.debug('no geolocation in Uwazi for this case')

                    if screenshot == '':
                        screenshot_alpha = []
                        screenshot2_alpha = []
                    else:
                        screenshot_alpha = [{
                                    "value": {
                                        "label": "screenshot",
                                        "url": screenshot
                                    }
                                }]
                        screenshot2_alpha = [{"value":screenshot}]

                    # Content
                    entity = {
                            'title': uwazi_title,
                            'template': self.uwazi_content_template_id, 
                            "type": "entity",
                            "documents": [],
                            'metadata': {
                                "description":[{"value":description}], 
                                "screenshot2":screenshot2_alpha,
                                "screenshot": screenshot_alpha,
                                "video_url1":[{"value":video_url1}],
                                "video_url2":[{"value":video_url2}],
                                "image_url1":[{"value":image_url1}],
                                "image_url2":[{"value":image_url2}],
                                "image_url3":[{"value":image_url3}],
                                "image_url4":[{"value":image_url4}],
                                # "generated_id":[{"value":"KJY5630-3351"}], # need to generate something here to send it
                                "generated_id":[{"value":entry_number}], 
                                # "date_posted":[{"value":1644155025}], # 2022/02/06 13:43:45
                                "date_posted":[{"value":unix_timestamp}], 
                                # "case": [{ "value": "06oxg0tt4m1m" } ],
                                # DM 10th Jun 25 - what if we can have a blank CASE_ID then just upload the content without the link to the case.
                                # I need to send an empty array rather than the mongo id
                                # "case": [{ "value": case_id_mongo } ],
                                # "case":[],
                                "case": [] if not case_id_mongo else [{ "value": case_id_mongo } ],
                                "geolocation_geolocation": geolocation_geolocation,
                                "upload_title":[{"value":upload_title}], 
                                "hash":[{"value":hash}], 
                                "link": [{
                                        "value": {
                                            "label": link,
                                            "url": link
                                        }
                                    }],
                                "archive_location": [{
                                        "value": {
                                            "label": archive_location,
                                            "url": archive_location
                                        }
                                    }]
                                }
                            }
                    
                    # uploads the new Content Entity
                    shared_id = uwazi_adapter.entities.upload(entity=entity, language='en')

                    if shared_id.startswith('Error'):
                        message = f"{entry_number} - {shared_id}"
                        logger.error(message)
                        import_to_uwazi_notes += message
                    else:
                        logger.success(f'Sent new Content to Uwazi - {uwazi_title}')
                        # if successful import then write date to spreadsheet
                        gw.set_cell(row, 'date_imported_to_uwazi',datetime.utcnow().replace(tzinfo=timezone.utc).isoformat())
                    
                    if import_to_uwazi_notes == '': import_to_uwazi_notes = 'success'

                    gw.set_cell(row, 'import_to_uwazi_notes',import_to_uwazi_notes)
                    continue # to next row of the sheet (don't want to run any more code below as have just sent data to Uwazi)

            # back to normal non uwazi
            status = gw.get_cell(row, "status", fresh=original_status in ["", None])
            # TODO: custom status parser(?) aka should_retry_from_status
            if status not in ["", None]:
                continue

            # Set in orchestration.yaml. Default is False
            if self.must_have_folder_name_for_archive_to_run:
                if not gw.get_cell(row, "folder"):
                    logger.warning(f"Folder name not set {self.sheet}:{gw.wks.title}, row {row} - skipping and continuing with run")
                    gw.set_cell(row, "status", "WARNING:Folder Name not set")
                    continue

            # All checks done - archival process starts here
            m = Metadata().set_url(url)
            self._set_context(m, gw, row)
            yield m

    def _set_context(self, m: Metadata, gw: GWorksheet, row: int) -> Metadata:
        # TODO: Check folder value not being recognised
        m.set_context("gsheet", {"row": row, "worksheet": gw})

        if gw.get_cell_or_default(row, "folder", "") is None:
            folder = ""
        else:
            folder = slugify(gw.get_cell_or_default(row, "folder", "").strip())
        if len(folder):
            if self.use_sheet_names_in_stored_paths:
                m.set_context("folder", os.path.join(folder, slugify(self.sheet), slugify(gw.wks.title)))
            else:
                m.set_context("folder", folder)

    def should_process_sheet(self, sheet_name: str) -> bool:
        if len(self.allow_worksheets) and sheet_name not in self.allow_worksheets:
            # ALLOW rules exist AND sheet name not explicitly allowed
            return False
        return not (self.block_worksheets and sheet_name in self.block_worksheets)

    def missing_required_columns(self, gw: GWorksheet) -> list:
        missing = []
        for required_col in ["url", "status"]:
            if not gw.col_exists(required_col):
                missing.append(required_col)
        return missing

    def started(self, item: Metadata) -> None:
        logger.info(f"STARTED {item}")
        gw, row = self._retrieve_gsheet(item)
        gw.set_cell(row, "status", "Archive in progress")
        logger.info(f" row: {row} on {gw.wks.spreadsheet.title} : {gw.wks.title}")

    def failed(self, item: Metadata, reason: str) -> None:
        logger.error(f"FAILED {item}")
        self._safe_status_update(item, f"Archive failed {reason}")

    def aborted(self, item: Metadata) -> None:
        logger.warning(f"ABORTED {item}")
        self._safe_status_update(item, "")

    def fetch(self, item: Metadata) -> Union[Metadata, bool]:
        """check if the given item has been archived already"""
        return False

    def done(self, item: Metadata, cached: bool = False) -> None:
        """archival result ready - should be saved to DB"""
        logger.success(f"DONE {item.get_url()}")
        gw, row = self._retrieve_gsheet(item)
        # self._safe_status_update(item, 'done')

        # DM - success log message showing the row, sheet and tab
        spreadsheet = gw.wks.spreadsheet.title
        worksheet = gw.wks.title
        logger.success(f" row {row} on {spreadsheet} : {worksheet}")

        cell_updates = []
        row_values = gw.get_row(row)

        def batch_if_valid(col, val, final_value=None):
            final_value = final_value or val
            try:
                if self.allow_overwrite_of_spreadsheet_cells:
                    if val and gw.col_exists(col):
                        existing_value = gw.get_cell(row_values, col)
                        if existing_value:
                            logger.info(f"Overwriting spreadsheet cell {col}={existing_value} with {final_value} in {gw.wks.title} row {row}")
                        cell_updates.append((row, col, final_value))
                else:
                    if val and gw.col_exists(col) and gw.get_cell(row_values, col) == "":
                        cell_updates.append((row, col, final_value))
            except Exception as e:
                logger.error(f"Unable to batch {col}={final_value} due to {e}")

        status_message = item.status
        if cached:
            status_message = f"[cached] {status_message}"
        cell_updates.append((row, "status", status_message))

        media: Media = item.get_final_media()
        if hasattr(media, "urls"):
            batch_if_valid("archive", "\n".join(media.urls))
        batch_if_valid("date", True, get_current_timestamp())
        batch_if_valid("title", item.get_title())
        batch_if_valid("text", item.get("content", ""))
        batch_if_valid("timestamp", item.get_timestamp())
        if media:
            batch_if_valid("hash", media.get("hash", "not-calculated"))

        # merge all pdq hashes into a single string, if present
        pdq_hashes = []
        all_media = item.get_all_media()
        for m in all_media:
            if pdq := m.get("pdq_hash"):
                pdq_hashes.append(pdq)
        if len(pdq_hashes):
            batch_if_valid("pdq_hash", ",".join(pdq_hashes))

        if (screenshot := item.get_media_by_id("screenshot")) and hasattr(screenshot, "urls"):
            batch_if_valid("screenshot", "\n".join(screenshot.urls))

        if (thumbnail := item.get_first_image("thumbnail")) and hasattr(thumbnail, "urls"):
            batch_if_valid("thumbnail", f'=IMAGE("{thumbnail.urls[0]}")')

        if browsertrix := item.get_media_by_id("browsertrix"):
            batch_if_valid("wacz", "\n".join(browsertrix.urls))
            batch_if_valid(
                "replaywebpage",
                "\n".join(
                    [
                        f"https://replayweb.page/?source={quote(wacz)}#view=pages&url={quote(item.get_url())}"
                        for wacz in browsertrix.urls
                    ]
                ),
            )

        # DM 10th Jun 25 - Uwazi helper to set images in spreadsheet so that it can upload them to Uwazi
        # only run this feature if the column exists in the definition ie in orchestration in the db (assume if first column exists, then others do)
        # DM 17th Jun 25 - this is now a general helper function that can be used for any spreadsheet
        image_and_video_url_feature = False
        try:
            _ = gw.col_exists('image_url1')
            image_and_video_url_feature = True
        except: pass

        if image_and_video_url_feature:
            # get first media
            # if there is no media then there will be a screenshot 
            # TODO - how about using screenshot_ in filename?

            # First media
            first_media_url = None
            try:
                first_media = all_media[0]
                # a screenshot has no source, so this returns None.
                first_media_url= first_media.get('src')

                # is it a twitter video?
                if (first_media_url is not None and '.mp4' in first_media_url):
                    # will only write to spreadsheet if the column is defined in orchestration
                    batch_if_valid('video_url1', first_media_url)
                # is it a youtubedlp video ie local?
                elif 'video' in first_media.mimetype:
                    first_media_url = first_media.urls[0]
                    batch_if_valid('video_url1', first_media_url)
                # instagram
                elif 'image/webp' in first_media.mimetype:
                    first_media_url = first_media.urls[0]
                    batch_if_valid('image_url1', first_media_url)
                else:
                    batch_if_valid('image_url1', first_media_url)
            except Exception as e:
                pass

            # DM 11th Jun 25 - if no first media then use screenshot
            if first_media_url is None:
                try:
                    first_media_url = item.get_media_by_id("screenshot").urls[0]
                    batch_if_valid('image_url1', first_media_url)
                except:
                    pass

            # Second media
            try:
                # if multiple videos then we have thumbnails which we don't want to consider
                # so lets filter out any with properties of id thumbnail_
                new_array = []
                for media in all_media[1:]:
                    dd = media.get('id')
                    if dd is None:
                        new_array.append(media) 
                second_media = new_array[0]
                second_media_url= second_media.get('src')

                # is it a twitter video?
                if ('.mp4' in second_media_url):
                    batch_if_valid('video_url2', second_media_url)
                else:
                    batch_if_valid('image_url2', second_media_url)
            except Exception as e:
                pass

            try:
                third_media = all_media[2]
                third_media_url= third_media.get('src')
                batch_if_valid('image_url3', third_media_url)
            except: pass

            try:
                fourth_media = all_media[3]
                fourth_media_url= fourth_media.get('src')
                batch_if_valid('image_url4', fourth_media_url)
            except: pass

            


        # DM 4th Jun 25 - saw this fail with a google api [503]: The service is currently unavailable.
        # so added a retry loop.
        attempt = 1
        while attempt <= 5:
            try:
                gw.batch_set_cell(cell_updates)
                break
            except Exception as e:
                logger.warning(f"Attempt {attempt} of batch_set_cell failed due to {e} ")
                attempt += 1
                time.sleep(5 * attempt) # linear backoff

    def _safe_status_update(self, item: Metadata, new_status: str) -> None:
        try:
            gw, row = self._retrieve_gsheet(item)
            gw.set_cell(row, "status", new_status)
        except Exception as e:
            logger.debug(f"Unable to update sheet: {e}")

    def _retrieve_gsheet(self, item: Metadata) -> Tuple[GWorksheet, int]:
        if gsheet := item.get_context("gsheet"):
            gw: GWorksheet = gsheet.get("worksheet")
            row: int = gsheet.get("row")
        elif self.sheet_id:
            logger.error(
                f"Unable to retrieve Gsheet for {item.get_url()}, GsheetDB must be used alongside GsheetFeeder."
            )

        return gw, row
