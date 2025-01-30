import pytest
import sys
from argparse import ArgumentParser
from auto_archiver.core.orchestrator import ArchivingOrchestrator
from auto_archiver.version import __version__
from auto_archiver.core.config import read_yaml, store_yaml

TEST_ORCHESTRATION = "tests/data/test_orchestration.yaml"
TEST_MODULES = "tests/data/test_modules/"

@pytest.fixture
def test_args():
    return ["--config", TEST_ORCHESTRATION,
            "--module_paths", TEST_MODULES,
            "--example_module.required_field", "some_value"] # just set this for normal testing, we will remove it later

@pytest.fixture
def orchestrator():
    yield ArchivingOrchestrator()
    # hack - the loguru logger starts with one logger, but if orchestrator has run before
    # it'll remove the default logger, add it back in:

    from loguru import logger

    if not logger._core.handlers.get(0):
        logger._core.handlers_count = 0
        logger.add(sys.stderr)
    # and remove the custom logger
    if logger._core.handlers.get(1):
        logger.remove(1)

@pytest.fixture
def basic_parser(orchestrator) -> ArgumentParser:
    return orchestrator.setup_basic_parser()

def test_setup_orchestrator(orchestrator):
    assert orchestrator is not None

def test_parse_config():
    pass

def test_parse_basic(basic_parser):
    args = basic_parser.parse_args(["--config", TEST_ORCHESTRATION])
    assert args.config_file == TEST_ORCHESTRATION

@pytest.mark.parametrize("mode", ["simple", "full"])
def test_mode(basic_parser, mode):
    args = basic_parser.parse_args(["--mode", mode])
    assert args.mode == mode

def test_mode_invalid(basic_parser, capsys):
    with pytest.raises(SystemExit) as exit_error:
        basic_parser.parse_args(["--mode", "invalid"])
    assert exit_error.value.code == 2
    assert "invalid choice" in capsys.readouterr().err

def test_version(basic_parser, capsys):
    with pytest.raises(SystemExit) as exit_error:
        basic_parser.parse_args(["--version"])
    assert exit_error.value.code == 0
    assert capsys.readouterr().out == f"{__version__}\n"

def test_help(orchestrator, basic_parser, capsys):

    args = basic_parser.parse_args(["--help"])
    assert args.help == True

    # test the show_help() on orchestrator
    with pytest.raises(SystemExit) as exit_error:
        orchestrator.show_help(args)

    assert exit_error.value.code == 0
    assert "Usage: auto-archiver [--help] [--version] [--config CONFIG_FILE]" in capsys.readouterr().out


def test_add_custom_modules_path(orchestrator, test_args):
    orchestrator.run(test_args)
    
    import auto_archiver
    assert "tests/data/test_modules/" in auto_archiver.modules.__path__

def test_add_custom_modules_path_invalid(orchestrator, caplog, test_args):

    orchestrator.run(test_args +  # we still need to load the real path to get the example_module 
                          ["--module_paths", "tests/data/invalid_test_modules/"])

    # assert False
    assert caplog.records[0].message == "Path 'tests/data/invalid_test_modules/' does not exist. Skipping..."


def test_check_required_values(orchestrator, caplog, test_args):
    # drop the example_module.required_field from the test_args
    test_args = test_args[:-2]

    with pytest.raises(SystemExit) as exit_error:
        orchestrator.run(test_args)

    assert caplog.records[1].message == "the following arguments are required: --example_module.required_field"

def test_get_required_values_from_config(orchestrator, test_args, tmp_path):

    # load the default example yaml, add a required field, then run the orchestrator
    test_yaml = read_yaml(TEST_ORCHESTRATION)
    test_yaml['example_module'] = {'required_field': 'some_value'}
    # write it to a temp file
    tmp_file = (tmp_path / "temp_config.yaml").as_posix()
    store_yaml(test_yaml, tmp_file)

    # run the orchestrator
    orchestrator.run(["--config", tmp_file, "--module_paths", TEST_MODULES])

    # should run OK, since there are no missing required fields

    # basic_args = basic_parser.parse_known_args(test_args)
    # test_yaml = read_yaml(TEST_ORCHESTRATION)
    # test_yaml['example_module'] = {'required_field': 'some_value'}

    # # monkey patch the example_module to have a 'configs' setting of 'my_var' with required=True
    # # load the module first
    # m = get_module_lazy("example_module")

    # orchestrator.setup_complete_parser(basic_args, test_yaml, unused_args=[])
    # assert orchestrator.config is not None