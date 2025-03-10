"""Thumbnail Enricher for generating visual previews of video files.

The `ThumbnailEnricher` processes video files in `Metadata` objects and
creates evenly distributed thumbnail images. These thumbnails provide
visual snapshots of the video's keyframes, helping users preview content
and identify important moments without watching the entire video.

"""

import ffmpeg
import os
from loguru import logger

from auto_archiver.core import Enricher
from auto_archiver.core import Media, Metadata
from auto_archiver.utils.misc import random_str


class ThumbnailEnricher(Enricher):
    """
    Generates thumbnails for all the media
    """

    def enrich(self, to_enrich: Metadata) -> None:
        """
        Uses or reads the video duration to generate thumbnails
        Calculates how many thumbnails to generate and at which timestamps based on the video duration, the number of thumbnails per minute and the max number of thumbnails.
        Thumbnails are equally distributed across the video duration.
        """
        logger.debug(f"generating thumbnails for {to_enrich.get_url()}")
        for m_id, m in enumerate(to_enrich.media[::]):
            if m.is_video():
                folder = os.path.join(self.tmp_dir, random_str(24))
                os.makedirs(folder, exist_ok=True)
                logger.debug(f"generating thumbnails for {m.filename}")
                duration = m.get("duration")

                if duration is None:
                    try:
                        probe = ffmpeg.probe(m.filename)
                        duration = float(
                            next(stream for stream in probe["streams"] if stream["codec_type"] == "video")["duration"]
                        )
                        to_enrich.media[m_id].set("duration", duration)
                    except Exception as e:
                        logger.error(f"error getting duration of video {m.filename}: {e}")
                        return

                num_thumbs = int(min(max(1, (duration / 60) * self.thumbnails_per_minute), self.max_thumbnails))
                timestamps = [duration / (num_thumbs + 1) * i for i in range(1, num_thumbs + 1)]

                thumbnails_media = []
                for index, timestamp in enumerate(timestamps):
                    output_path = os.path.join(folder, f"out{index}.jpg")
                    ffmpeg.input(m.filename, ss=timestamp).filter("scale", 512, -1).output(
                        output_path, vframes=1, loglevel="quiet"
                    ).run()

                    try:
                        thumbnails_media.append(
                            Media(filename=output_path)
                            .set("id", f"thumbnail_{index}")
                            .set("timestamp", "%.3fs" % timestamp)
                        )
                    except Exception as e:
                        logger.error(f"error creating thumbnail {index} for media: {e}")

                to_enrich.media[m_id].set("thumbnails", thumbnails_media)
