import ffmpeg, os, uuid
from loguru import logger

from . import Enricher
from ..core import Media, Metadata, ArchivingContext


class ThumbnailEnricher(Enricher):
    """
    Generates thumbnails for all the media
    """
    name = "thumbnail_enricher"

    def __init__(self, config: dict) -> None:
        # without this STEP.__init__ is not called
        super().__init__(config)

    @staticmethod
    def configs() -> dict:
        return {}

    def enrich(self, to_enrich: Metadata) -> None:
        logger.debug(f"generating thumbnails")
        for i, m in enumerate(to_enrich.media[::]):
            if m.is_video():
                folder = os.path.join(ArchivingContext.get_tmp_dir(), str(uuid.uuid4()))
                os.makedirs(folder, exist_ok=True)
                logger.debug(f"generating thumbnails for {m.filename}")
                fps, duration = 0.5, m.get("duration")
                if duration is not None:
                    duration = float(duration)
                    if duration < 60: fps = 10.0 / duration
                    elif duration < 120: fps = 20.0 / duration
                    else: fps = 40.0 / duration

                stream = ffmpeg.input(m.filename)
                stream = ffmpeg.filter(stream, 'fps', fps=fps).filter('scale', 512, -1)
                stream.output(os.path.join(folder, 'out%d.jpg')).run()

                thumbnails = os.listdir(folder)
                thumbnails_media = []
                for t, fname in enumerate(thumbnails):
                    if fname[-3:] == 'jpg':
                        thumbnails_media.append(Media(filename=os.path.join(folder, fname)).set("id", f"thumbnail_{t}"))
                to_enrich.media[i].set("thumbnails", thumbnails_media)
