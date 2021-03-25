import gspread
import subprocess
import argparse
import auto_archive

def main():
    parser = argparse.ArgumentParser(
        description="Automatically use youtube-dl to download media from a Google Sheet")
    parser.add_argument("--sheet", action="store", dest="sheet")

    args = parser.parse_args()

    print("Opening document " + args.sheet)

    gc = gspread.service_account()
    sh = gc.open(args.sheet)

    wks = sh.get_worksheet(0)
    values = wks.get_all_values()

    for i in range(1, len(values)):
        sheet_name = values[i][0]

        print("Processing " + sheet_name)

        auto_archive.process_sheet(sheet_name)

if __name__ == "__main__":
    main()
