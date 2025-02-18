# Module Documentation

These pages describe the core modules that come with `auto-archiver` and provide the main functionality for archiving websites on the internet. There are five core module types:

1. Feeders - these 'feed' information (the URLs) from various sources to the `auto-archiver` for processing
2. Extractors - these 'extract' the page data for a given URL that is fed in by a feeder
3. Enrichers - these 'enrich' the data extracted in the previous step with additional information
4. Storage - these 'store' the data in a persistent location (on disk, Google Drive etc.)
5. Databases - these 'store' the status of the entire archiving process in a log file or database.


```{include} modules/autogen/module_list.md
```


```{toctree}
:maxdepth: 1
:caption: Core Modules
:hidden:

modules/config_cheatsheet
modules/feeder
modules/extractor
modules/enricher
modules/storage
modules/database
modules/formatter
```