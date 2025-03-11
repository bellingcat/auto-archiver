import os
import hashlib
from importlib.metadata import version

from slugify import slugify
from loguru import logger
import opentimestamps
from opentimestamps.calendar import RemoteCalendar, DEFAULT_CALENDAR_WHITELIST
from opentimestamps.core.timestamp import Timestamp, DetachedTimestampFile
from opentimestamps.core.notary import PendingAttestation, BitcoinBlockHeaderAttestation
from auto_archiver.core import Enricher
from auto_archiver.core import Metadata, Media
from auto_archiver.version import __version__


class OpentimestampsEnricher(Enricher):
    """
    Uses OpenTimestamps to create and verify timestamps for files. OpenTimestamps is a service that 
    timestamps data using the Bitcoin blockchain, providing a decentralized and secure way to prove 
    that data existed at a certain point in time.

    The enricher hashes files in the archive and creates timestamp proofs that can later be verified.
    These proofs are stored alongside the original files and can be used to verify the timestamp
    even if the OpenTimestamps calendar servers are unavailable.
    """

    def setup(self):
        # Initialize any resources needed
        pass

    def cleanup(self) -> None:
        # Clean up any resources used
        pass

    def enrich(self, to_enrich: Metadata) -> None:
        url = to_enrich.get_url()
        logger.debug(f"OpenTimestamps timestamping files for {url=}")

        # Get the media files to timestamp
        media_files = [m for m in to_enrich.media if m.get("filename") and not m.get("opentimestamps")]
        
        if not media_files:
            logger.warning(f"No files found to timestamp in {url=}")
            return

        timestamp_files = []
        for media in media_files:
            try:
                # Get the file path from the media
                file_path = media.get("filename")
                if not os.path.exists(file_path):
                    logger.warning(f"File not found: {file_path}")
                    continue
                
                # Create timestamp for the file
                logger.debug(f"Creating timestamp for {file_path}")
                
                # Hash the file
                with open(file_path, 'rb') as f:
                    file_bytes = f.read()
                file_hash = hashlib.sha256(file_bytes).digest()
                
                # Create a timestamp with the file hash
                timestamp = Timestamp(file_hash)
                
                # Create a detached timestamp file with the timestamp
                detached_timestamp = DetachedTimestampFile(timestamp)
                
                # Submit to calendar servers
                if self.use_calendars:
                    logger.debug(f"Submitting timestamp to calendar servers for {file_path}")
                    calendars = []
                    whitelist = DEFAULT_CALENDAR_WHITELIST
                    
                    if self.calendar_whitelist:
                        whitelist = set(self.calendar_whitelist)
                    
                    # Create calendar instances
                    for url in self.calendar_urls:
                        if url in whitelist:
                            calendars.append(RemoteCalendar(url))
                    
                    # Submit the hash to each calendar
                    for calendar in calendars:
                        try:
                            calendar_timestamp = calendar.submit(file_hash)
                            timestamp.merge(calendar_timestamp)
                            logger.debug(f"Successfully submitted to calendar: {calendar.url}")
                        except Exception as e:
                            logger.warning(f"Failed to submit to calendar {calendar.url}: {e}")
                else:
                    logger.info("Skipping calendar submission as per configuration")
                
                # Save the timestamp proof to a file
                timestamp_path = os.path.join(self.tmp_dir, f"{os.path.basename(file_path)}.ots")
                with open(timestamp_path, 'wb') as f:
                    detached_timestamp.serialize(f)
                
                # Create media for the timestamp file
                timestamp_media = Media(filename=timestamp_path)
                timestamp_media.set("source_file", os.path.basename(file_path))
                timestamp_media.set("opentimestamps_version", opentimestamps.__version__)
                
                # Verify the timestamp if needed
                if self.verify_timestamps:
                    verification_info = self.verify_timestamp(detached_timestamp)
                    for key, value in verification_info.items():
                        timestamp_media.set(key, value)
                
                timestamp_files.append(timestamp_media)
                
                # Update the original media to indicate it's been timestamped
                media.set("opentimestamps", True)
                media.set("opentimestamp_file", timestamp_path)
                
            except Exception as e:
                logger.warning(f"Error while timestamping {media.get('filename')}: {e}")
        
        # Add timestamp files to the metadata
        if timestamp_files:
            for ts_media in timestamp_files:
                to_enrich.add_media(ts_media)
            
            to_enrich.set("opentimestamped", True)
            to_enrich.set("opentimestamps_count", len(timestamp_files))
            logger.success(f"{len(timestamp_files)} OpenTimestamps proofs created for {url=}")
        else:
            logger.warning(f"No successful timestamps created for {url=}")
    
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
                    info["type"] = "pending"
                    info["uri"] = attestation.uri.decode('utf-8')
                
                elif isinstance(attestation, BitcoinBlockHeaderAttestation):
                    info["type"] = "bitcoin"
                    info["block_height"] = attestation.height
                
                attestation_info.append(info)
            
            result["attestations"] = attestation_info
            
            # For at least one confirmed attestation
            if any(a.get("type") == "bitcoin" for a in attestation_info):
                result["verified"] = True
            else:
                result["verified"] = False
                result["pending"] = True
        else:
            result["verified"] = False
            result["pending"] = False
        
        return result