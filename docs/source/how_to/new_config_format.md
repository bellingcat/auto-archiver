# Upgrading to 0.13 Configuration Format

```{note} This how-to is only relevant for people who used Auto Archiver before February 2025 (versions prior to 0.13).

If you are new to Auto Archiver, then you are already using the latest configuration format and this how-to is not relevant for you.
```

Version 0.13 of Auto Archiver has breaking changes in the configuration format, which means earlier configuration formats will not work without slight modifications.

## How do I know if I need to update my configuration format?

There are two simple ways to check if you need to update your format:

1. When you try and run auto-archiver using your existing configuration file, you get an error like the following:

```AssertionError: No feeders were configured. Make sure to set at least one feeder in your configuration file or on the command line (using --feeders)
```

2. Within your configuration file, you have a `feeder:` option. This is the old format. An example old format:
```{yaml}
steps:
  feeder: gsheet_feeder
...
```

## Updating your configuration file

To update your configuration file, you can either:

### 1. Manually edit the configuration file and change the values.

This is recommended if you want to keep all your old settings. Follow the steps below to change the relevant settings:

1. Feeder & Formatter Steps Settings

The feeder and formatter settings have been changed from a single string to a list.

`steps.feeder (string)` → `steps.feeders (list)`
`steps.formatter (string)` → `steps.formatters (list)`

Example:
```{yaml}
steps:
   feeder: cli_feeder
   - telegram_archiver
   ...
   formatter: html_formatter

# the above should be changed to:
steps:
   feeders:
   - cli_feeder
   ...
    formatters:
    - html_formatter
```

```{note} Auto Archiver still only supports one feeder and formatter, but from v0.13 onwards they must be added to the configuration file as a list.
```

2. Extractor (formerly Archiver) Steps Settings

With v0.13 of Auto Archiver, the `archivers` have been renamed to `extractors` to reflect the work they actually do - extract information from a URL. Change the configuration by renaming:

`steps.archivers` → `steps.extractors`

The names of the actual modules have also changed, so for any extractor modules you have enabled, you will need to rename the `archiver` part to `extractor`. Some examples:

`telethon_archiver` → `telethon_extractor`
`wacz_archiver_enricher` → `wacz_extractor_enricher`
`vk_archiver` → `vk_extractor`

Additionally, the `youtube_archiver` has been renamed to `generic_extractor` and should be considere the default/fallback extractor. Read more about the [generic extractor](../modules/autogen/extractor/generic_extractor.md).

Example:
```{yaml}
steps:
   ...
   archivers:
   - telethon_archiver
   - youtube_archiver
   - vk_archiver

# renaming 'archiver' to 'extractor', and renaming the youtube_archiver the above config will become:
steps:
   ...
   extractors:
   - telethon_extractor
   - vk_extractor
   - generic_extractor

```

3. Redundant / Obsolete Modules

With v0.13 of Auto Archiver, the following modules have been removed and their features have been built in to the generic_extractor:

* `twitter_archiver` - use the `generic_extractor` for general extraction, or the `twitter_api_extractor` for API access.
* `tiktok_archiver` - use the `generic_extractor` to extract TikTok videos.

If you have either of these set in your configuration under `steps:` you should remove them.



### 2. Auto-generate a new config, then copy over your settings.

Using this method, you can have Auto Archiver auto-generate a configuration file for you, then you can copy over the desired settings from your old config file. This is probably the easiest method and quickest to setup, but it may require some trial and error as you copy over your settings.

First, move your existing `orchestration.yaml` file to a different folder or rename it.

Then, you can generate a `simple` or `full` config using:

```{code} console
>>> # generate a simple config
>>> auto-archiver 
>>> # config will be written to orchestration.yaml
>>>
>>> # generate a full config
>>> auto-archiver --mode=full
>>>
```

After this, copy over any settings from your old config to the new config.


