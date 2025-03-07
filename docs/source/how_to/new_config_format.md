# Upgrading from v0.12

```{note} This how-to is only relevant for people who used Auto Archiver before February 2025 (versions prior to 0.13).

If you are new to Auto Archiver, then you are already using the latest configuration format and this how-to is not relevant for you.
```

Versions 0.13+ of Auto Archiver has breaking changes in the configuration format, which means earlier configuration formats will not work without slight modifications.

## How do I know if I need to update my configuration format?

There are two simple ways to check if you need to update your format:

1. When you try and run auto-archiver using your existing configuration file, you get an error about no feeders or formatters being configured, like:

```{code} console
AssertionError: No feeders were configured. Make sure to set at least one feeder in
your configuration file or on the command line (using --feeders)
```

2. Within your configuration file, you have a `feeder:` option. This is the old format. An example old format:
```{code} yaml

steps:
  feeder: cli_feeder
...
```

## Updating your configuration file

To update your configuration file, you can either:

### 1. Manually edit the configuration file and change the values.

This is recommended if you want to keep all your old settings. Follow the steps below to change the relevant settings:

#### a) Feeder & Formatter Steps Settings

The feeder and formatter settings have been changed from a single string to a list.

- `steps.feeder (string)` → `steps.feeders (list)`
- `steps.formatter (string)` → `steps.formatters (list)`

Example:

```{code} yaml

steps:
   feeder: cli_feeder
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

#### b) Extractor (formerly Archiver) Steps Settings

With v0.13 of Auto Archiver, `archivers` have been renamed to `extractors` to better reflect what they actually do - extract information from a URL. Change the configuration by renaming:

- `steps.archivers` → `steps.extractors`

The names of the actual modules have also changed, so for any extractor modules you have enabled, you will need to rename the `archiver` part to `extractor`. Some examples:

- `telethon_archiver` → `telethon_extractor`
- `wacz_archiver_enricher` → `wacz_extractor_enricher`
- `wayback_archiver_enricher` → `wayback_extractor_enricher`
- `vk_archiver` → `vk_extractor`


#### c) Module Renaming


The `youtube_archiver` has been renamed to `generic_extractor` as it is considered the default/fallback extractor. Read more about the [generic extractor](../modules/autogen/extractor/generic_extractor.md).

The `atlos` modules have been merged into one, as have the `gsheets` feeder and database.

- `atlos_feeder` → `atlos_feeder_db_storage`
- `atlos_storage` → `atlos_feeder_db_storage`
- `atlos_db` → `atlos_feeder_db_storage`
- `gsheet_feeder` → `gsheet_feeder_db`
- `gsheet_db` → `gsheet_feeder_db`


Example:
```{code} yaml
steps:
   feeders:
   - gsheet_feeder_db # formerly gsheet_feeder
   ...
   extractors: # formerly 'archivers'
   - telethon_extractor # formerly telethon_archiver
   - generic_extractor # formerly youtube_archiver
   - vk_extractor # formerly vk_archiver
   databases:
   - gsheet_feeder_db # formerly gsheet_db
   ...

```


#### d) Redundant / Obsolete Modules

With v0.13 of Auto Archiver, the following modules have been removed and their features have been built in to the generic_extractor. You should remove them from the 'steps' section of your configuration file:

* `twitter_archiver` - use the `generic_extractor` for general extraction, or the `twitter_api_extractor` for API access.
* `tiktok_archiver` - use the `generic_extractor` to extract TikTok videos.


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


