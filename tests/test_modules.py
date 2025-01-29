import sys
import pytest
from auto_archiver.core.module import get_module_lazy, BaseModule, LazyBaseModule, _LAZY_LOADED_MODULES
from auto_archiver.core.extractor import Extractor

@pytest.fixture
def example_module():
    yield get_module_lazy("example_module", ["tests/data/"])
    # cleanup
    _LAZY_LOADED_MODULES.pop("example_module")

def test_get_module_lazy(example_module):
    assert example_module.name == "example_module"
    assert example_module.display_name == "Example Module"

    assert example_module.manifest is not None


def test_load_module_abc_check(example_module):

    # example_module is an extractor but doesn't have the 'download' method, should raise an ABC error
    with pytest.raises(TypeError) as load_error:
        example_module.load({})
    assert "Can't instantiate abstract class ExampleModule with abstract method download" in str(load_error.value)

    
def test_load_module(example_module, monkeypatch):
    # hack - remove the 'download' method from the required methods of Extractor
    monkeypatch.setattr(Extractor, "__abstractmethods__", set())

    # setup the module, and check that config is set to the default values
    loaded_module = example_module.load({})
    assert loaded_module is not None
    assert isinstance(loaded_module, BaseModule)
    assert loaded_module.name == "example_module"
    assert loaded_module.display_name == "Example Module"
    assert loaded_module.config["example_module"] ==  {"csv_file" : "db.csv"}

    # check that the vlaue is set on the module itself
    assert loaded_module.csv_file == "db.csv"

@pytest.mark.parametrize("module_name", ["cli_feeder", "local_storage", "generic_extractor", "html_formatter", "csv_db"])
def test_load_modules(module_name):
    # test that specific modules can be loaded
    module = get_module_lazy(module_name)
    assert module is not None
    assert isinstance(module, LazyBaseModule)
    assert module.name == module_name

    loaded_module = module.load({})
    assert isinstance(loaded_module, BaseModule)
    assert loaded_module.name == module_name
    assert loaded_module.display_name == module.display_name

    # check that default settings are applied
    default_config = module.configs
    assert loaded_module.name in loaded_module.config.keys()


@pytest.mark.parametrize("module_name", ["cli_feeder", "local_storage", "generic_extractor", "html_formatter", "csv_db"])
def test_lazy_base_module(module_name):
    lazy_module = get_module_lazy(module_name)

    assert lazy_module is not None
    assert isinstance(lazy_module, LazyBaseModule)
    assert lazy_module.name == module_name
    assert len(lazy_module.display_name) > 0
    assert module_name in lazy_module.path
    assert isinstance(lazy_module.manifest, dict)

    assert lazy_module.requires_setup == lazy_module.manifest.get("requires_setup", True)
    assert len(lazy_module.entry_point) > 0
    assert len(lazy_module.configs) > 0
    assert len(lazy_module.description) > 0
    assert len(lazy_module.version) > 0


