import gspread
import argparse
import auto_archive
from loguru import logger

def main():
    parser = argparse.ArgumentParser(
        description="Automatically use youtube-dl to download media from a Google Sheet")
    parser.add_argument("--sheet", action="store", dest="sheet")

    args = parser.parse_args()

    logger.info("Opening document " + args.sheet)

    gc = gspread.service_account(filename='service_account.json')
    sh = gc.open(args.sheet)

    wks = sh.get_worksheet(0)
    values = wks.get_all_values()

    for i in range(11, len(values)):
        sheet_name = values[i][0]

        logger.info("Processing " + sheet_name)

        auto_archive.process_sheet(sheet_name)

if __name__ == "__main__":
    main()
