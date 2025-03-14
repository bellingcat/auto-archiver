from auto_archiver.modules.html_formatter import HtmlFormatter
from auto_archiver.core import Metadata, Media


def test_format(setup_module):
    formatter = setup_module(HtmlFormatter)

    metadata = Metadata().set("content", "Hello, world!").set_url("https://example.com")

    final_media = formatter.format(metadata)
    assert isinstance(final_media, Media)
    assert ".html" in final_media.filename
    with open(final_media.filename, "r", encoding="utf-8") as f:
        content = f.read()
        assert "Hello, world!" in content
    assert final_media.mimetype == "text/html"
    assert "SHA-256:" in final_media.get("hash")
