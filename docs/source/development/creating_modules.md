# Creating Your Own Modules

Modules are what's used to extend `auto-archiver` to process different websites or media, and/or transform the data in a way that suits your needs. In most cases, the [](../core_modules.md) should be sufficient for every day use, but the most common use-cases for making your own Modules include:

1. Extracting data from a website which doesn't work with the current core extractors.
2. Enriching or altering the data before saving with additional information that the core enrichers do not offer.
3. Storing your data in a different format/location from what the core storage providers offer.

## Setting up the folder structure

1. First, decide what type of module you wish to create. Check the types of modules on the [](../core_modules.md) page to decide what type you need. (Note: a module can be more than one type, more on that below)
2. Create a new python package (a folder) with the name of your module (in this tutorial, we'll call it `awesome_extractor`).
3. Create the `__manifest__.py` and an the `awesome_extractor.py` files in this folder.

When done, you should have a module structure as follows:

```
.
├── awesome_extractor
│   ├── __manifest__.py
│   └── awesome_extractor.py
``` 

Check out the [core modules](https://github.com/bellingcat/auto-archiver/tree/main/src/auto_archiver/modules) in the `auto-archiver` repository for examples of the folder structure for real-world modules.

## Populating the Manifest File

The manifest file is where you define the core information of your module. It is a python dict containing important information, here's an example file:

```{code} python
:filename: myfile.py

def setup():
   pass
```

```{include} ../../../tests/data/test_modules/example_module/__manifest__.py
:name: __manifest__.py
:literal:
:parser: python
```

## Creating the Python Code

The next step is to create your module code. First, create a class which should subclass the base module types from `auto_archiver.core`, here's an example class for the `awesome_extractor` module which is an `extractor`:

```{code-block} python
:filename: awesome_extractor.py

from auto_archiver.core import Extractor, Metadata

def AwesomeExtractor(Extractor):

    def download(self, item: Metadata) -> Metadata | False:
      url = item.get_url()
      # download the content and create the metadata object
      metadata = ...
      return metadata
```
