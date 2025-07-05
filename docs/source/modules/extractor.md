# Extractor Modules

Extractor modules are used to extract the content of a given URL. Typically, one extractor will work for one website or platform (e.g. a Telegram extractor or an Instagram), however, there are several wide-ranging extractors which work for a wide range of websites.

Extractors that are able to extract content from a wide range of websites include:
1. Generic Extractor: parses videos and images on sites using the powerful yt-dlp library.
2. Antibot Extractor: uses a headless browser to bypass bot detection and extract content.
3. WACZ Extractor: runs a web browser to 'browse' the URL and save a copy of the page in WACZ format.
4. Wayback Machine Extractor: sends pages to the Wayback machine for archiving, and stores the archived link.

```{include} autogen/extractor.md
```

```{toctree}
:maxdepth: 1
:hidden:
:glob:
autogen/extractor/*
```