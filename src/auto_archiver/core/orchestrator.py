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

        try: 
            for a in self.archivers: a.setup()
        except (KeyboardInterrupt, Exception) as e:
            logger.error(f"Error during setup of archivers: {e}\n{traceback.format_exc()}")
            self.cleanup()


    def cleanup(self)->None:
        logger.info("Cleaning up")
        for a in self.archivers: a.cleanup()

    def feed(self) -> Generator[Metadata]:
        for item in self.feeder:
            yield self.feed_item(item)
        self.cleanup()

    def feed_item(self, item: Metadata) -> Metadata:
        """
        Takes one item (URL) to archive and calls self.archive, additionally:
            - catches keyboard interruptions to do a clean exit
            - catches any unexpected error, logs it, and does a clean exit
        """
        try:
            ArchivingContext.reset()
            with tempfile.TemporaryDirectory(dir="./") as tmp_dir:
                ArchivingContext.set_tmp_dir(tmp_dir)
                return self.archive(item)
        except KeyboardInterrupt:
            # catches keyboard interruptions to do a clean exit
            logger.warning(f"caught interrupt on {item=}")
            for d in self.databases: d.aborted(item)
            self.cleanup()
            exit()
        except Exception as e:
            logger.error(f'Got unexpected error on item {item}: {e}\n{traceback.format_exc()}')
            for d in self.databases: d.failed(item)


    def archive(self, result: Metadata) -> Union[Metadata, None]:
        """
            Runs the archiving process for a single URL
            1. Each archiver can sanitize its own URLs
            2. Check for cached results in Databases, and signal start to the databases
            3. Call Archivers until one succeeds
            4. Call Enrichers
            5. Store all downloaded/generated media
            6. Call selected Formatter and store formatted if needed
        """
        original_url = result.get_url()

        # 1 - sanitize - each archiver is responsible for cleaning/expanding its own URLs
        url = original_url
        for a in self.archivers: url = a.sanitize_url(url)
        result.set_url(url)
        if original_url != url: result.set("original_url", original_url)

        # 2 - notify start to DBs, propagate already archived if feature enabled in DBs
        cached_result = None
        for d in self.databases:
            d.started(result)
            if (local_result := d.fetch(result)):
                cached_result = (cached_result or Metadata()).merge(local_result)
        if cached_result:
            logger.debug("Found previously archived entry")
            for d in self.databases:
                d.done(cached_result, cached=True)
            return cached_result

        # 3 - call archivers until one succeeds
        for a in self.archivers:
            logger.info(f"Trying archiver {a.name} for {url}")
            try:
                result.merge(a.download(result))
                if result.is_success(): break
            except Exception as e: 
                logger.error(f"ERROR archiver {a.name}: {e}: {traceback.format_exc()}")

        # 4 - call enrichers to work with archived content
        for e in self.enrichers:
            try: e.enrich(result)
            except Exception as exc: 
                logger.error(f"ERROR enricher {e.name}: {exc}: {traceback.format_exc()}")

        # 5 - store all downloaded/generated media
        result.store()

        # 6 - format and store formatted if needed
        if (final_media := self.formatter.format(result)):
            final_media.store(url=url)
            result.set_final_media(final_media)

        if result.is_empty():
            result.status = "nothing archived"

        # signal completion to databases and archivers
        for d in self.databases: d.done(result)

        return result
