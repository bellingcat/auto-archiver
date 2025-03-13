import pytest
from auto_archiver.core.module import ModuleFactory, LazyBaseModule
from auto_archiver.core.base_module import BaseModule


@pytest.fixture
def example_module():
    import auto_archiver

    module_factory = ModuleFactory()
    # previous_path = auto_archiver.modules.__path__
    auto_archiver.modules.__path__.append("tests/data/test_modules/")
    return module_factory.get_module_lazy("example_module")


def test_get_module_lazy(example_module):
    assert example_module.name == "example_module"
    assert example_module.display_name == "Example Module"

    assert example_module.manifest is not None


def test_python_dependency_check(example_module):
    # example_module requires loguru, which is not installed
    # monkey patch the manifest to include a nonexistnet dependency
    example_module.manifest["dependencies"]["python"] = ["does_not_exist"]

    with pytest.raises(SystemExit) as load_error:
        example_module.load({})

    assert load_error.value.code == 1


def test_binary_dependency_check(example_module):
    # example_module requires ffmpeg, which is not installed
    # monkey patch the manifest to include a nonexistnet dependency
    example_module.manifest["dependencies"]["binary"] = ["does_not_exist"]


def test_module_dependency_check_loads_module(example_module):
    # example_module requires cli_feeder, which is not installed
    # monkey patch the manifest to include a nonexistnet dependency
    example_module.manifest["dependencies"]["python"] = ["hash_enricher"]

    module_factory = example_module.module_factory

    loaded_module = example_module.load({})
    assert loaded_module is not None

    # check the dependency is loaded
    assert module_factory._lazy_modules["hash_enricher"] is not None
    assert module_factory._lazy_modules["hash_enricher"]._instance is not None


def test_load_module(example_module):
    # setup the module, and check that config is set to the default values
    loaded_module = example_module.load({})
    assert loaded_module is not None
    assert isinstance(loaded_module, BaseModule)
    assert loaded_module.name == "example_module"
    assert loaded_module.display_name == "Example Module"
    assert loaded_module.config["example_module"] == {"csv_file": "db.csv"}

    # check that the vlaue is set on the module itself
    assert loaded_module.csv_file == "db.csv"


@pytest.mark.parametrize("module_name", ["local_storage", "generic_extractor", "html_formatter", "csv_db"])
def test_load_modules(module_name):
    # test that specific modules can be loaded
    module = ModuleFactory().get_module_lazy(module_name)
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
    defaults = {k: v.get("default") for k, v in default_config.items()}
    assert loaded_module.config[module_name] == defaults


@pytest.mark.parametrize("module_name", ["local_storage", "generic_extractor", "html_formatter", "csv_db"])
def test_lazy_base_module(module_name):
    lazy_module = ModuleFactory().get_module_lazy(module_name)

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
