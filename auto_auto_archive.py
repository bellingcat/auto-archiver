import shutil
import auto_archive
from loguru import logger
from configs import Config
from storages import Storage
from utils import mkdir_if_not_exists


def main():
    c = Config()
    c.parse()
    logger.info(f'Opening document {c.sheet} to look for sheet names to archive')

    gc = c.gsheets_client
    sh = gc.open(c.sheet)

    wks = sh.get_worksheet(0)
    values = wks.get_all_values()

    mkdir_if_not_exists(Storage.TMP_FOLDER)
    for i in range(11, len(values)):
        c.sheet = values[i][0]
        logger.info(f"Processing {c.sheet}")
        auto_archive.process_sheet(c)
    c.destroy_webdriver()
    shutil.rmtree(Storage.TMP_FOLDER)


if __name__ == "__main__":
    main()
