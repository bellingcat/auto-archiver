# Upgrading from v1.0.1

```{note} This how-to is only relevant for people who used Auto Archiver before June 2025 (versions prior to 1.1.0).

If you are new to Auto Archiver, then you are already using the latest configuration format and this how-to is not relevant for you.
```

Versions 1.1.0+ of Auto Archiver has breaking changes in the configuration format, which means earlier configuration formats will not work without slight modifications.


## Dropping `vk_extractor` module
We have dropped the `vk_extractor` because of problems in a project we relied on. You will need to remove it from your configuration file, otherwise you will see an error like:

```{code} console
Module 'vk_extractor' not found. Are you sure it's installed/exists?
```

## Dropping `screenshot_enricher` module
We have dropped the `screenshot_enricher` module because a new `antibot_extractor_enricher` (see below) module replaces its functionality more robustly and with less dependency hassle on geckodriver/firefox. You will need to remove it from your configuration file, otherwise you will see an error like:

```{code} console
Module 'screenshot_enricher' not found. Are you sure it's installed/exists?
```


## New `antibot_extractor_enricher` module and VkDropin
We have added a new [`antibot_extractor_enricher`](../modules/autogen/extractor/antibot_extractor_enricher.md) module that uses a computer-controlled browser to extract content from websites that use anti-bot measures. You can add it to your configuration file like this:

```{code} yaml
steps:
  extractors:
    - antibot_extractor_enricher

  # or alternatively, if you want to use it as an enricher:
  enrichers:
    - antibot_extractor_enricher
```

It will take a full page screenshot, a PDF capture, extract HTML source code, and any other relevant media. 

It comes with Dropins that we will be adding and maintaining. 

> Dropin: A module with site-specific behaviours that is loaded automatically. You don't need to add them to your configuration steps for them to run. Sometimes they need `authentication` configurations though.

One such Dropin is the VkDropin which uses this automated browser to access VKontakte (VK) pages. You should add a username/password to the configuration file if you get authentication blocks from VK, to do so use the [authentication settings](authentication_how_to.md):

```{code} yaml
authentication:
  vk.com:
    username: your_username
    password: your_password
```

See all available Dropins in [the source code](https://github.com/bellingcat/auto-archiver/tree/main/src/auto_archiver/modules/antibot_extractor_enricher/dropins). Usually each Dropin needs its own authentication settings, similarly to the VkDropin.