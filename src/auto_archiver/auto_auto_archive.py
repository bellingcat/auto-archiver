
#TODO: refactor GDriveStorage before merging to main
# is it possible to have something like this with the new pipeline?


# # import tempfile
# import auto_archive
# from loguru import logger
# from configs import Config
# from storages import Storage


# def main():
#     c = Config()
#     c.parse()
#     logger.info(f'Opening document {c.sheet} to look for sheet names to archive')

#     gc = c.gsheets_client
#     sh = gc.open(c.sheet)

#     wks = sh.get_worksheet(0)
#     values = wks.get_all_values()

#     with tempfile.TemporaryDirectory(dir="./") as tmpdir:
#         Storage.TMP_FOLDER = tmpdir
#         for i in range(11, len(values)):
#             c.sheet = values[i][0]
#             logger.info(f"Processing {c.sheet}")
#             auto_archive.process_sheet(c)
#         c.destroy_webdriver()


# if __name__ == "__main__":
#     main()
