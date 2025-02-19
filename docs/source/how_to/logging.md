# Logging

Auto Archiver's logs can be helpful for debugging problematic archiving processes. This guide shows you how to use the logs to 

## Setting up logging

Logging settings can be set on the command line or using the orchestration config file ([learn more](../installation/configuration)). A special `logging` section defines the logging options.

#### Logging Level

There are 7 logging levels in total, with 4 commonly used levels. They are: `DEBUG`, `INFO`, `WARNING` and `ERROR`.

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

### Logging to a file

As default, auto-archiver will log to the console. But if you wish to store your logs for future reference, or you are running the auto-archiver from within code a implementation, then you may with to enable file logging. This can be done by setting the `file:` config value in the logging settings.

**Rotation:** For file logging, you can choose to 'rotate' your log files (creating new log files) so they do not get too large. Change this by setting the 'rotation' option in your logging settings. For a full list of rotation options, see the [loguru docs](https://loguru.readthedocs.io/en/stable/overview.html#easier-file-logging-with-rotation-retention-compression).

```{code} yaml
:caption: orchestration.yaml

logging:
    ...
    file: /my/log/file.log
    rotation: 1 day
```

### Full logging example

The below example logs only `WARNING` logs to the console and to the file `/my/file.log`, rotating that file once per week:

```{code} yaml
:caption: orchestration.yaml

logging:
    level: WARNING
    file: /my/file.log
    rotation: 1 week
```