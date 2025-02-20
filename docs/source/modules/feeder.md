# Feeder Modules

Feeder modules are used to feed URLs into the Auto Archiver for processing. Feeders can take these URLs from a variety of sources, such as a file, a database, or the command line.

The default feeder is the command line feeder (`cli_feeder`), which allows you to input URLs directly into `auto-archiver` from the command line.

Command line feeder usage:
```{code} bash
auto-archiver [options] -- URL1 URL2 ...
```

```{include} autogen/feeder.md
```

```{toctree}
:depth: 1
:glob:
:hidden:
autogen/feeder/*
```