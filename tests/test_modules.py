import pytest
from auto_archiver.core.module import get_module, BaseModule, LazyBaseModule

@pytest.mark.parametrize("module_name", ["cli_feeder", "local_storage", "generic_extractor", "html_formatter", "csv_db"])
def test_load_modules(module_name):
    # test that specific modules can be loaded
    module = get_module(module_name)
    assert module is not None
    assert isinstance(module, LazyBaseModule)
    assert module.name == module_name

    loaded_module = module.load()
    assert isinstance(loaded_module, BaseModule)

    # test module setup
    loaded_module.setup(config={})

    assert loaded_module.config == {}


@pytest.mark.parametrize("module_name", ["cli_feeder", "local_storage", "generic_extractor", "html_formatter", "csv_db"])
def test_lazy_base_module(module_name):
    lazy_module = get_module(module_name)

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


