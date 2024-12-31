import tempfile

from auto_archiver.core.context import ArchivingContext


ArchivingContext.reset(full_reset=True)
ArchivingContext.set_tmp_dir(tempfile.gettempdir())