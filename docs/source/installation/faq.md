# Frequently Asked Questions


### Q: What websites does the Auto Archiver support?
**A:** The Auto Archiver works for a large variety of sites. Firstly, the Auto Archiver can download
and archive any video website supported by YT-DLP, a powerful video-downloading tool ([full list of of
sites here](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)). Aside from these sites,
there are various different 'Extractors' for specific websites. See the full list of extractors that 
are available on the [extractors](../modules/extractor.md) page. Some sites supported include:

* Twitter
* Instagram
* Telegram
* VKontact
* Tiktok
* Bluesky

```{note} What websites the Auto Archiver can archie depends on what extractors you have enabled in
your configuration. See [configuration](./configurations.md) for more info.
```

### Q: Does the Auto Archiver only work for social media posts ?
**A:** No, the Auto Archiver can archive any web page on the internet, not just social media posts.
However, for social media posts Auto Archiver can extract more relevant/useful information (such as 
post comments, likes, author etc.) which may not be available for a generic website. If you are looking
to more generally archive webpages, then you should make sure to enable the [](../modules/autogen/extractor/wacz_extractor_enricher.md)
and the [](../modules/autogen/extractor/wayback_extractor_enricher.md).

### Q: What kind of data is stored for each webpage that's archived?
**A:** This depends on the website archived, but more generally, for social media posts any videos and photos in
the post will be archived. For video sites, the video will be downloaded separately. For most of these sites, additional
metadata such as published date, uploader/author and ratings/comments will also be saved. Additionally, further data can be
saved depending on the enrichers that you have enabled. Some other types of data saved are timestamps if you have the 
[](../modules/autogen/enricher/timestamping_enricher.md) or [](../modules/autogen/enricher/opentimestamps_enricher.md) enabled,
screenshots of the web page with the [](../modules/autogen/enricher/screenshot_enricher.md), and for videos, thumbnails of the
video with the [](../modules/autogen/enricher/thumbnail_enricher.md). You can also store things like hashes (SHA256, or pdq hashes)
with the various hash enrichers.

### Q: Where is my data stored?
**A:** With the default configuration, data is stored on your local computer in the `local_storage` folder. You can adjust these settings by
changing the [storage modules](../modules/storage.md) you have enabled. For example, you could choose to store your data in an S3 bucket or 
on Google Drive. 

```{note}
You can choose to store your data in multiple places, for example your local drive **and** an S3 bucket for redundancy.
```

### Q: What should I do is something doesn't work?
**A:** First, read through the log files to see if you can find a specific reason why something isn't working. Learn more about logging
and how to enable debug logging in the [Logging Howto](../how_to/logging.md).

If you cannot find an answer in the logs, then try searching this documentation or existing / closed issues on the [Github Issue Tracker](https://github.com/bellingcat/auto-archiver/issues?q=is%3Aissue%20). If you still cannot find an answer, then consider opening an issue on the Github Issue Tracker or asking in the Bellingcat Discord
'Auto Archiver' group.

#### Common reasons why an archiving might not work:

* The website may have temporarily adjusted its settings - sometimes sites like Telegram or Twitter adjust their scraping protection settings. Often,
waiting a day or two and then trying again can work.
* The site requires you to be logged in - make sure the 
* The website you're trying to archive has changed its settings/structure. Make sure you're using the latest version of Auto Archiver and try again.
