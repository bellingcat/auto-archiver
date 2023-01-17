from __future__ import annotations
from ast import List
from typing import Union, Dict
from dataclasses import dataclass

from archivers import Archiverv2
from feeders import Feeder
from formatters import Formatter
from media import Media
from storages import StorageV2
from enrichers import Enricher
from databases import Database
from metadata import Metadata

import tempfile, time, traceback
from loguru import logger


"""
how not to couple the different pieces of logic
due to the use of constants for the metadata keys?
perhaps having methods on the Metadata level that can be used to fetch a limited number of
keys, never using strings but rather methods?
eg: m = Metadata() 
    m.get("screenshot") vs m.get_all()
    m.get_url()
    m.get_hash()
    m.get_main_file().get_title()
    m.get_screenshot() # this method should only exist because of the Screenshot Enricher
    # maybe there is a way for Archivers and Enrichers and Storages to add their own methdods
    # which raises still the Q of how the database, eg., knows they exist? 
    # maybe there's a function to fetch them all, and each Database can register wathever they get
    # for eg the GoogleSheets will only register based on the available column names, it knows what it wants
    # and if it's there: great, otherwise business as usual.
    # and a MongoDatabase could register all data, for example.
    # 
How are Orchestrators created? from a configuration file?
    orchestrator = ArchivingOrchestrator(config)
        # Config contains 1 URL, or URLs, from the command line
        # OR a feeder which is described in the config file
        # config.get_feeder() # if called as docker run --url "http...." then the uses the default filter
        # if config.yaml says config
    orchestrator.start()


Example applications:
1. auto-archiver for GSheets
2. archiver for URL: feeder is CLIFeeder(config.cli.urls="") # --urls="u1,u2"
3. archiver backend for a UI that implements a REST API, the API calls CLI

Cisticola considerations:
1. By isolating the archiving logic into "Archiving only pieces of logic" these could simply call cisticola.tiktok_scraper(user, pass)
2. So the auto-archiver becomes like a puzzle and fixes to Cisticola scrapers can immediately benefit it, and contributions are focused on a single source or scraping
"""


class ArchivingOrchestrator:
    def __init__(self, config) -> None:
        # in config.py we should test that the archivers exist and log mismatches (blocking execution)
        # identify each formatter, storage, database, etc
        # self.feeder = Feeder.init(config.feeder, config.get(config.feeder))

        # Is it possible to overwrite config.yaml values? it could be useful: share config file and modify gsheet_feeder.sheet via CLI
        # where does that update/processing happen? in config.py
        # reflection for Archiver to know which child classes it has? use Archiver.__subclasses__
        # self.archivers = [
        #     Archiver.init(a, config)
        #     for a in config.archivers
        # ]
        self.feeder: Feeder = config.feeder
        self.formatter: Formatter = config.formatter
        self.enrichers = config.enrichers
        self.archivers: List[Archiverv2] = config.archivers
        self.databases: List[Database] = config.databases
        self.storages: List[StorageV2] = config.storages

        for a in self.archivers: a.setup()

        self.formatters = []
        # self.formatters = [
        #     Formatter.init(f, config)
        #     for f in config.formatters
        # ]

        # self.storages = [
        #     Storage.init(s, config)
        #     for s in config.storages
        # ]

        # self.databases = [
        #     Database.init(f, config)
        #     for f in config.formatters
        # ]

        # these rules are checked in config.py
        # assert len(archivers) > 1, "there needs to be at least one Archiver"

    def feed(self) -> list(Metadata):
        for item in self.feeder:
            print("ARCHIVING", item)
            try:
                with tempfile.TemporaryDirectory(dir="./") as tmp_dir:
                    item.set_tmp_dir(tmp_dir)
                    result = self.archive(item)
                    print(result)
            except KeyboardInterrupt:
                # catches keyboard interruptions to do a clean exit
                logger.warning(f"caught interrupt on {item=}")
                for d in self.databases: d.aborted(item)
                exit()
            except Exception as e:
                logger.error(f'Got unexpected error on item {item}: {e}\n{traceback.format_exc()}')
                for d in self.databases: d.failed(item)

            print("holding on 5min")
            time.sleep(300)

            # how does this handle the parameters like folder which can be different for each archiver?
            # the storage needs to know where to archive!!
            # solution: feeders have context: extra metadata that they can read or ignore,
            # all of it should have sensible defaults (eg: folder)
            # default feeder is a list with 1 element

    def archive(self, result: Metadata) -> Union[Metadata, None]:
        url = result.get_url()
        # TODO: clean urls
        for a in self.archivers:
            url = a.clean_url(url)
        result.set_url(url)
        # should_archive = False
        # for d in self.databases: should_archive |= d.should_process(url)
        # should storages also be able to check?
        # for s in self.storages: should_archive |= s.should_process(url)

        # if not should_archive:
        #     print("skipping")
        #     return "skipping"

        # signal to DB that archiving has started
        # and propagate already archived if it exists
        cached_result = None
        for d in self.databases:
            # are the databases to decide whether to archive?
            # they can simply return True by default, otherwise they can avoid duplicates. should this logic be more granular, for example on the archiver level: a tweet will not need be scraped twice, whereas an instagram profile might. the archiver could not decide from the link which parts to archive,
            # instagram profile example: it would always re-archive everything
            # maybe the database/storage could use a hash/key to decide if there's a need to re-archive
            d.started(result)
            if (local_result := d.fetch(result)):
                cached_result = (cached_result or Metadata()).merge(local_result)
        if cached_result and not cached_result.rearchivable:
            for d in self.databases:
                d.done(cached_result)
            return cached_result

        # vk, telethon, ...
        for a in self.archivers:
            # with automatic try/catch in download + archived (+ the other ops below)
            # should the archivers come with the config already? are there configs which change at runtime?
            # think not, so no need to pass config as parameter
            # do they need to be refreshed with every execution?
            # this is where the Hashes come from, the place with access to all content
            # the archiver does not have access to storage
            # a.download(result) # TODO: refactor so there's not merge here
            result.merge(a.download(result))
            # TODO: fix logic
            if True or result.is_success(): break

        # what if an archiver returns multiple entries and one is to be part of HTMLgenerator?
        # should it call the HTMLgenerator as if it's not an enrichment?
        # eg: if it is enable: generates an HTML with all the returned media, should it include enrichers? yes
        # then how to execute it last? should there also be post-processors? are there other examples?
        # maybe as a PDF? or a Markdown file
        # side captures: screenshot, wacz, webarchive, thumbnails, HTMLgenerator
        for e in self.enrichers:
            e.enrich(result)

        # store media
        for s in self.storages:
            for m in result.media:
                s.store(m, result)  # modifies media
                # Media can be inside media properties, examples include transformations on original media
                for prop in m.properties.values():
                    if isinstance(prop, Media):
                        s.store(prop, result)
                    if isinstance(prop, list) and len(prop)>0 and isinstance(prop[0], Media):
                        for prop_media in prop:
                            s.store(prop_media, result)

        # formatters, enrichers, and storages will sometimes look for specific properties: eg <li>Screenshot: <img src="{res.get("screenshot")}"> </li>
        # TODO: should there only be 1 formatter?
        # for f in self.formatters:
        #     result.merge(f.format(result))
        # final format and store it
        if (final_media := self.formatter.format(result)):
            for s in self.storages:
                s.store(final_media, result)
            result.set_final_media(final_media)

        # signal completion to databases (DBs, Google Sheets, CSV, ...)
        # a hash registration service could be one database: forensic archiving
        result.cleanup()
        for d in self.databases: d.done(result)

        return result
