import os
import traceback

from auto_archiver.utils.custom_logger import logger
import opentimestamps
from opentimestamps.calendar import RemoteCalendar, DEFAULT_CALENDAR_WHITELIST
from opentimestamps.core.timestamp import Timestamp, DetachedTimestampFile
from opentimestamps.core.notary import PendingAttestation, BitcoinBlockHeaderAttestation
from opentimestamps.core.op import OpSHA256
from opentimestamps.core import serialize
from auto_archiver.core import Enricher
from auto_archiver.core import Metadata, Media
from auto_archiver.utils.misc import get_current_timestamp


class OpentimestampsEnricher(Enricher):
    def enrich(self, to_enrich: Metadata) -> None:
        logger.debug("OpenTimestamps timestamping files")

        # Get the media files to timestamp
        media_files = [m for m in to_enrich.media if m.filename and not m.get("opentimestamps")]
        if not media_files:
            logger.debug("No files found to timestamp")
            return

        timestamp_files = []
        for media in media_files:
            try:
                # Get the file path from the media
                file_path = media.filename
                if not os.path.exists(file_path):
                    logger.warning(f"File not found: {file_path}")
                    continue

                # Create timestamp for the file - hash is SHA256
                # Note: hash is hard-coded to SHA256 and does not use hash_enricher to set it.
                # SHA256 is the recommended hash, ref: https://github.com/bellingcat/auto-archiver/pull/247#discussion_r1992433181
                logger.debug(f"Creating timestamp for {file_path}")
                file_hash = None
                with open(file_path, "rb") as f:
                    file_hash = OpSHA256().hash_fd(f)

                if not file_hash:
                    logger.warning(f"Failed to hash file for timestamping, skipping: {file_path}")
                    continue

                # Create a timestamp with the file hash
                timestamp = Timestamp(file_hash)

                # Create a detached timestamp file with the hash operation and timestamp
                detached_timestamp = DetachedTimestampFile(OpSHA256(), timestamp)

                # Submit to calendar servers
                submitted_to_calendar = False

                logger.debug(f"Submitting timestamp to calendar servers for {file_path}")
                calendars = []
                whitelist = DEFAULT_CALENDAR_WHITELIST

                if self.calendar_whitelist:
                    whitelist = set(self.calendar_whitelist)

                # Create calendar instances
                calendar_urls = []
                for url in self.calendar_urls:
                    if url in whitelist:
                        calendars.append(RemoteCalendar(url))
                        calendar_urls.append(url)

                # Submit the hash to each calendar
                for calendar in calendars:
                    try:
                        calendar_timestamp = calendar.submit(file_hash)
                        timestamp.merge(calendar_timestamp)
                        logger.debug(f"Successfully submitted to calendar: {calendar.url}")
                        submitted_to_calendar = True
                    except Exception as e:
                        logger.warning(f"Failed to submit to calendar {calendar.url}: {e}")

                # If all calendar submissions failed, add pending attestations
                if not submitted_to_calendar and not timestamp.attestations:
                    logger.error(
                        f"Failed to submit to any calendar for {file_path}. **This file will not be timestamped.**"
                    )
                    media.set("opentimestamps", False)
                    continue

                # Save the timestamp proof to a file
                timestamp_path = os.path.join(self.tmp_dir, f"{os.path.basename(file_path)}.ots")
                try:
                    with open(timestamp_path, "wb") as f:
                        # Create a serialization context and write to the file
                        ctx = serialize.BytesSerializationContext()
                        detached_timestamp.serialize(ctx)
                        f.write(ctx.getbytes())
                except Exception as e:
                    logger.warning(f"Failed to serialize timestamp file: {e} {traceback.format_exc()}")
                    continue

                # Create media for the timestamp file
                timestamp_media = Media(filename=timestamp_path)
                # explicitly set the mimetype, normally .ots files are 'application/vnd.oasis.opendocument.spreadsheet-template'
                timestamp_media.mimetype = "application/vnd.opentimestamps"
                timestamp_media.set("opentimestamps_version", opentimestamps.__version__)

                verification_info = self.verify_timestamp(detached_timestamp)
                for key, value in verification_info.items():
                    timestamp_media.set(key, value)

                media.set("opentimestamp_files", [timestamp_media])
                timestamp_files.append(timestamp_media.filename)
                # Update the original media to indicate it's been timestamped
                media.set("opentimestamps", True)

            except Exception as e:
                logger.warning(f"Error while timestamping {media.filename}: {e} {traceback.format_exc()}")

        # Add timestamp files to the metadata
        if timestamp_files:
            to_enrich.set("opentimestamped", True)
            to_enrich.set("opentimestamps_count", len(timestamp_files))
            logger.info(f"{len(timestamp_files)} OpenTimestamps proofs created")
        else:
            to_enrich.set("opentimestamped", False)
            logger.warning("No successful timestamps created")

    def verify_timestamp(self, detached_timestamp):
        """
        Verify a timestamp and extract verification information.

        Args:
            detached_timestamp: The detached timestamp to verify.

        Returns:
            dict: Information about the verification result.
        """
        result = {}

        # Check if we have attestations
        attestations = list(detached_timestamp.timestamp.all_attestations())
        result["attestation_count"] = len(attestations)

        if attestations:
            attestation_info = []
            for msg, attestation in attestations:
                info = {}

                # Process different types of attestations
                if isinstance(attestation, PendingAttestation):
                    info["status"] = "pending"
                    info["uri"] = attestation.uri

                elif isinstance(attestation, BitcoinBlockHeaderAttestation):
                    info["status"] = "confirmed"
                    info["block_height"] = attestation.height

                info["last_check"] = get_current_timestamp()

                attestation_info.append(info)

            result["attestations"] = attestation_info

            # For at least one confirmed attestation
            if any("confirmed" in a.get("status") for a in attestation_info):
                result["verified"] = True
            else:
                result["verified"] = False
        else:
            result["verified"] = False
        result["last_updated"] = get_current_timestamp()

        return result
