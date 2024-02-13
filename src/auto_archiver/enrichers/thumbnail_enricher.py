import ffmpeg, os
from loguru import logger

from . import Enricher
from ..core import Media, Metadata, ArchivingContext
from ..utils.misc import random_str


class ThumbnailEnricher(Enricher):
    """
    Generates thumbnails for all the media
    """
    name = "thumbnail_enricher"

    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)
        self.thumbnails_per_second = int(self.thumbnails_per_minute) / 60
        self.max_thumbnails = int(self.max_thumbnails)

    @staticmethod
    def configs() -> dict:
        return {
            "thumbnails_per_minute": {"default": 60, "help": "how many thumbnails to generate per minute of video, can be limited by max_thumbnails"},
            "max_thumbnails": {"default": 16, "help": "limit the number of thumbnails to generate per video, 0 means no limit"},
        }
    
    def enrich(self, to_enrich: Metadata) -> None:
        """
        Uses or reads the video duration to generate thumbnails
        Calculates how many thumbnails to generate and at which timestamps based on the video duration, the number of thumbnails per minute and the max number of thumbnails.
        Thumbnails are equally distributed across the video duration.
        """
        logger.debug(f"generating thumbnails for {to_enrich.get_url()}")
        for m_id, m in enumerate(to_enrich.media[::]):
            if m.is_video():
                folder = os.path.join(ArchivingContext.get_tmp_dir(), random_str(24))
                os.makedirs(folder, exist_ok=True)
                logger.debug(f"generating thumbnails for {m.filename}")
                duration = m.get("duration")

                if duration is None:
                    try:
                        probe = ffmpeg.probe(m.filename)
                        duration = float(next(stream for stream in probe['streams'] if stream['codec_type'] == 'video')['duration'])
                        to_enrich.media[m_id].set("duration", duration)
                    except Exception as e:
                        logger.error(f"error getting duration of video {m.filename}: {e}")
                        return

                num_thumbs = int(min(max(1, duration * self.thumbnails_per_second), self.max_thumbnails))
                timestamps = [duration / (num_thumbs + 1) * i for i in range(1, num_thumbs + 1)]

                thumbnails_media = []
                for index, timestamp in enumerate(timestamps):
                    output_path = os.path.join(folder, f"out{index}.jpg")
                    ffmpeg.input(m.filename, ss=timestamp).filter('scale', 512, -1).output(output_path, vframes=1, loglevel="quiet").run()

                    try:
                        thumbnails_media.append(Media(
                            filename=output_path)
                            .set("id", f"thumbnail_{index}")
                            .set("timestamp", "%.3fs" % timestamp)
                        )
                    except Exception as e:
                        logger.error(f"error creating thumbnail {index} for media: {e}")

                to_enrich.media[m_id].set("thumbnails", thumbnails_media)
