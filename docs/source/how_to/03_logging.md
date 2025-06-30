# Keeping Logs

Auto Archiver's logs can be helpful for debugging problematic archiving processes. This guide shows you how to use the logs configuration.

## Setting up logging

Logging settings can be set on the command line or using the orchestration config file ([learn more](../installation/configuration)). A special `logging` section defines the logging options.

#### Enabling or Disabling Logging

Logging to the console is enabled by default. If you want to globally disable Auto Archiver's logging, then you can set `enabled: false` in your `logging` config file:

```{code} yaml
:caption: orchestration.yaml
...
logging:
   enabled: false
...
```

```{note}
This will disable all logs from Auto Archiver, but it does not disable logs for other tools that the Auto Archiver uses (for example: yt-dlp, firefox or ffmpeg). These logs will still appear in your console.
```

#### Logging Level

There are 7 logging levels in total, with 5 of them used in this tool. They are: `DEBUG`, `INFO`, `SUCCESS`, `WARNING` and `ERROR`. If you select a level, only that and higher (more serious) levels will be included. `DEBUG` is the most verbose, while `ERROR` is the least verbose. 

Change the warning level by setting the value in your orchestration config file:

```{code} yaml
:caption: orchestration.yaml

...
logging:
    level: DEBUG # or INFO / WARNING / ERROR
...
```

For normal usage, it is recommended to use the `INFO` level, or if you prefer quieter logs with less information, you can use the `WARNING` level. If you encounter issues with the archiving, then it's recommended to enable the `DEBUG` level.

```{note} To learn about all logging levels, see the [loguru documentation](https://loguru.readthedocs.io/en/stable/api/logger.html)
```

### Logging Format
By default, the console logs are formatted in a human-readable way and the file logs are formatted in JSON. This is new from version 1.1.1. If you want to change the format of the console logs to JSON too you can set the `format:` option in your logging settings. 

```{code} yaml
:caption: orchestration.yaml

logging:
    format: json
```

When the Auto Archiver is writing logs it will include context about specific tasks, so if you are archiving a URL from a Google Sheet, both the URL (and a unique `trace_id` for that URL's archiving attempt) and the Spreadsheet name and row will be included in the logs. This is useful for debugging and understanding what the Auto Archiver is doing.

Using JSON allows you to easily parse the logs and extract specific information, tools like [`jq`](https://jqlang.org/) can be used to filter and search through the logs.

### Logging to a file

As default, auto-archiver will log to the console. But if you wish to store your logs for future reference, or you are running the auto-archiver from within code a implementation, then you may wish to enable file logging. This can be done by setting the `file:` config value in the logging settings.

**Rotation:** For file logging, you can choose to 'rotate' your log files (creating new log files) so they do not get too large. Change this by setting the 'rotation' option in your logging settings. For a full list of rotation options, see the [loguru docs](https://loguru.readthedocs.io/en/stable/overview.html#easier-file-logging-with-rotation-retention-compression).

```{code} yaml
:caption: orchestration.yaml

logging:
    ...
    file: /my/log/file.log
    rotation: 1 day
```

### Logging each level to a different file
If you want to log each level to a different file, you can do this by setting the `each_level_in_separate_file:` option to `true` and also setting your `file:` name, a new file will be created for each of the 5 levels used, by appending the `0_level` name to the file like so `your_file.log.1_error`. In this case the `level:` option is ignored, and all levels will be logged. 


```{code} yaml
:caption: orchestration.yaml

logging:
    each_level_in_separate_file: true
    file: /my/logs/file.log 
```
This will create the following files:
- `/my/logs/file.log.1_debug`
- `/my/logs/file.log.2_info`
- `/my/logs/file.log.3_success`
- `/my/logs/file.log.4_warning`
- `/my/logs/file.log.5_error`

### Full logging example

The below example logs only `DEBUG` logs to the console and to the file `/my/file.log`, rotating that file once per week:

```{code} yaml
:caption: orchestration.yaml

logging:
    level: DEBUG
    format: json
    file: /my/file.log
    rotation: 1 week
```