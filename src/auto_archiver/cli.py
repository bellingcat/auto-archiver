import tempfile, json
import auto_archive
from loguru import logger
from configs import Config
from storages import Storage
from slugify import slugify


def main():
    c = Config()
    c.parse()
    url = c.url
    if not url:
        logger.error("Invalid URL: '{url}'")
        return
    logger.info(f'Archiving "{url=}".')
    with tempfile.TemporaryDirectory(dir="./") as tmpdir:
        Storage.TMP_FOLDER = tmpdir
        result = auto_archive.archive_url(c, url, "", f"{url=}", False)
        c.destroy_webdriver()
    key = f"media_{slugify(url)}.json"
    with open(key, "w", encoding="utf-8") as outf:
        json.dump(result.media, outf, ensure_ascii=False, indent=4)
    c.get_storage().upload(key, key)
    print(result)
    return result


if __name__ == "__main__":
    main()
