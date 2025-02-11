# Extractor Modules

Extractor modules are used to extract the content of a given URL. Typically, one extractor will work for one website or platform (e.g. a Telegram extractor or an Instagram), however, there are several wide-ranging extractors which work for a wide range of websites.

Extractors that are able to extract content from a wide range of websites include:
1. Generic Extractor: parses videos and images on sites using the powerful yt-dlp library.
2. Wayback Machine Extractor: sends pages to the Waygback machine for archiving, and stores the link.
3. WACZ Extractor: runs a web browser to 'browse' the URL and save a copy of the page in WACZ format. 

```{include} autogen/extractor.md
```

```{toctree}
:depth: 1
:glob:
autogen/extractor/*
```