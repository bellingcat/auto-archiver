from __future__ import annotations
from typing import Generator, Union, List

from .context import ArchivingContext

from ..archivers import Archiver
from ..feeders import Feeder
from ..formatters import Formatter
from ..storages import Storage
from ..enrichers import Enricher
from ..databases import Database
from .metadata import Metadata

import tempfile, traceback
from loguru import logger


class ArchivingOrchestrator:
    def __init__(self, config) -> None:
        self.feeder: Feeder = config.feeder
        self.formatter: Formatter = config.formatter
        self.enrichers: List[Enricher] = config.enrichers
        self.archivers: List[Archiver] = config.archivers
        self.databases: List[Database] = config.databases
        self.storages: List[Storage] = config.storages
        ArchivingContext.set("storages", self.storages, keep_on_reset=True)

        for a in self.archivers: a.setup()

    def feed(self) -> Generator[Metadata]:
        for item in self.feeder:
            yield self.feed_item(item)

    def feed_item(self, item: Metadata) -> Metadata:
        try:
            ArchivingContext.reset()
            with tempfile.TemporaryDirectory(dir="./") as tmp_dir:
                ArchivingContext.set_tmp_dir(tmp_dir)
                return self.archive(item)
        except KeyboardInterrupt:
            # catches keyboard interruptions to do a clean exit
            logger.warning(f"caught interrupt on {item=}")
            for d in self.databases: d.aborted(item)
            exit()
        except Exception as e:
            logger.error(f'Got unexpected error on item {item}: {e}\n{traceback.format_exc()}')
            for d in self.databases: d.failed(item)

        # how does this handle the parameters like folder which can be different for each archiver?
        # the storage needs to know where to archive!!
        # solution: feeders have context: extra metadata that they can read or ignore,
        # all of it should have sensible defaults (eg: folder)
        # default feeder is a list with 1 element

    def archive(self, result: Metadata) -> Union[Metadata, None]:
        original_url = result.get_url()

        # 1 - cleanup
        # each archiver is responsible for cleaning/expanding its own URLs
        url = original_url
        for a in self.archivers: url = a.sanitize_url(url)
        result.set_url(url)
        if original_url != url: result.set("original_url", original_url)

        # 2 - rearchiving logic + notify start to DB
        # archivers can signal whether the content is rearchivable: eg: tweet vs webpage
        for a in self.archivers: result.rearchivable |= a.is_rearchivable(url)
        logger.debug(f"{result.rearchivable=} for {url=}")

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
            logger.debug("Found previously archived entry")
            for d in self.databases:
                d.done(cached_result)
            return cached_result

        # 3 - call archivers until one succeeds
        for a in self.archivers:
            logger.info(f"Trying archiver {a.name} for {url}")
            try:
                # Q: should this be refactored so it's just a.download(result)?
                result.merge(a.download(result))
                if result.is_success(): break
            except Exception as e: logger.error(f"Unexpected error with archiver {a.name}: {e}: {traceback.format_exc()}")

        # what if an archiver returns multiple entries and one is to be part of HTMLgenerator?
        # should it call the HTMLgenerator as if it's not an enrichment?
        # eg: if it is enable: generates an HTML with all the returned media, should it include enrichers? yes
        # then how to execute it last? should there also be post-processors? are there other examples?
        # maybe as a PDF? or a Markdown file

        # 4 - call enrichers: have access to archived content, can generate metadata and Media
        # eg: screenshot, wacz, webarchive, thumbnails
        for e in self.enrichers:
            try: e.enrich(result)
            except Exception as exc: logger.error(f"Unexpected error with enricher {e.name}: {exc}: {traceback.format_exc()}")

        # 5 - store media
        # looks for Media in result.media and also result.media[x].properties (as list or dict values)
        result.store()

        # 6 - format and store formatted if needed
        # enrichers typically need access to already stored URLs etc
        if (final_media := self.formatter.format(result)):
            final_media.store(url=url)
            result.set_final_media(final_media)

        if result.is_empty():
            result.status = "nothing archived"

        # signal completion to databases (DBs, Google Sheets, CSV, ...)
        for d in self.databases: d.done(result)

        return result
