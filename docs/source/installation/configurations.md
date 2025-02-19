
# Configuration

This section of the documentation provides guidelines for configuring the tool.

## Configuring using a file

The recommended way to configure auto-archiver for long-term and deployed projects is a configuration file, typically called `orchestration.yaml`. This is a YAML file containing all the settings for your entire workflow.

The structure of orchestration file is split into 2 parts: `steps` (what [steps](../flow_overview.md) to use) and `configurations` (settings for different modules), here's a simplification:

A default `orchestration.yaml` will be created for you the first time you run auto-archiver (without any arguments). Here's what it looks like:

<details>
<summary>View exampleorchestration.yaml</summary>

```{literalinclude} ../example.orchestration.yaml
   :language: yaml
   :caption: orchestration.yaml
```

</details>

## Configuring from the Command Line

You can run auto-archiver directly from the command line, without the need for a configuration file, command line arguments are parsed using the format `module_name.config_value`. For example, a config value of `api_key` in the `instagram_extractor` module would be passed on the command line with the flag `--instagram_extractor.api_key=API_KEY`.

The command line arguments are useful for testing or editing config values and enabling/disabling modules on the fly. When you are happy with your settings, you can store them back in your configuration file by passing the `-s/--store` flag on the command line.

```bash
auto-archiver --instagram_extractor.api_key=123 --other_module.setting --store
# will store the new settings into the configuration file (default: orchestration.yaml)
```

```{note} Arguments passed on the command line override those saved in your settings file. Save them to your config file using the -s or --store flag
```

## Seeing all Configuration Options

View the configurable settings for the core modules on the individual doc pages for each [](../core_modules.md).
You can also view all settings available for the modules you have on your system using the `--help` flag in auto-archiver.

```{code-block} console
:caption: Example output when using the --help flag with auto-archiver
$ auto-archiver --help
...
Positional Arguments:
  urls                  URL(s) to archive, either a single URL or a list of urls, should not come from config.yaml

Options:
  --help, -h            show a full help message and exit
  --version             show program's version number and exit
  --config CONFIG_FILE  the filename of the YAML configuration file (defaults to 'config.yaml')
  --mode {simple,full}  the mode to run the archiver in
  -s, --store, --no-store
                        Store the created config in the config file
  --module_paths MODULE_PATHS [MODULE_PATHS ...]
                        additional paths to search for modules
  --feeders STEPS.FEEDERS [STEPS.FEEDERS ...]
                        the feeders to use
  --enrichers STEPS.ENRICHERS [STEPS.ENRICHERS ...]
                        the enrichers to use
  --extractors STEPS.EXTRACTORS [STEPS.EXTRACTORS ...]
                        the extractors to use
  --databases STEPS.DATABASES [STEPS.DATABASES ...]
                        the databases to use
  --storages STEPS.STORAGES [STEPS.STORAGES ...]
                        the storages to use
  --formatters STEPS.FORMATTERS [STEPS.FORMATTERS ...]
                        the formatter to use
  --authentication AUTHENTICATION
                        A dictionary of sites and their authentication methods (token, username etc.) that extractors can use to log into a website. If passing this on the command line, use a JSON string. You may
                        also pass a path to a valid JSON/YAML file which will be parsed.
  --logging.level {INFO,DEBUG,ERROR,WARNING}
                        the logging level to use
  --logging.file LOGGING.FILE
                        the logging file to write to
  --logging.rotation LOGGING.ROTATION
                        the logging rotation to use

Wayback Machine Enricher:
  Submits the current URL to the Wayback Machine for archiving and returns either a job ID or the...

  --wayback_extractor_enricher.timeout TIMEOUT
                        seconds to wait for successful archive confirmation from wayback, if more than this passes the result contains the job_id so the status can later be checked manually.
  --wayback_extractor_enricher.if_not_archived_within IF_NOT_ARCHIVED_WITHIN
                        only tell wayback to archive if no archive is available before the number of seconds specified, use None to ignore this option. For more information:
                        https://docs.google.com/document/d/1Nsv52MvSjbLb2PCpHlat0gkzw0EvtSgpKHu4mk0MnrA
  --wayback_extractor_enricher.key KEY
                        wayback API key. to get credentials visit https://archive.org/account/s3.php
  --wayback_extractor_enricher.secret SECRET
                        wayback API secret. to get credentials visit https://archive.org/account/s3.php
  --wayback_extractor_enricher.proxy_http PROXY_HTTP
                        http proxy to use for wayback requests, eg http://proxy-user:password@proxy-ip:port
  --wayback_extractor_enricher.proxy_https PROXY_HTTPS
                        https proxy to use for wayback requests, eg https://proxy-user:password@proxy-ip:port
```

