import sys
import pytest

from auto_archiver.__main__ import main


@pytest.fixture
def orchestration_file_path(tmp_path):
    return (tmp_path / "example_orch.yaml").as_posix()

@pytest.fixture
def orchestration_file(orchestration_file_path):
    def _orchestration_file(content=''):
        with open(orchestration_file_path, "w") as f:
            f.write(content)
        return orchestration_file_path
    
    return _orchestration_file

@pytest.fixture
def autoarchiver(tmp_path, monkeypatch, request):
    def _autoarchiver(args=[]):

        def cleanup():
            from loguru import logger
            if not logger._core.handlers.get(0):
                logger._core.handlers_count = 0
                logger.add(sys.stderr)

        request.addfinalizer(cleanup)

        # change dir to tmp_path
        monkeypatch.chdir(tmp_path)
        with monkeypatch.context() as m:
            m.setattr(sys, "argv", ["auto-archiver"] + args)
            return main()

    return _autoarchiver


def test_run_auto_archiver_no_args(caplog, autoarchiver):
    with pytest.raises(SystemExit):
        autoarchiver()

    assert "provide at least one URL via the command line, or set up an alternative feeder" in caplog.text

def test_run_auto_archiver_invalid_file(caplog, autoarchiver):
    # exec 'auto-archiver' on the command lin
    with pytest.raises(SystemExit):
        autoarchiver(["--config", "nonexistent_file.yaml"])

    assert "Make sure the file exists and try again, or run without th" in caplog.text

def test_run_auto_archiver_empty_file(caplog, autoarchiver, orchestration_file):
    # create a valid (empty) orchestration file
    path = orchestration_file(content="")
    # exec 'auto-archiver' on the command lin
    with pytest.raises(SystemExit):
        autoarchiver(["--config", path])

    # should treat an empty file as if there is no file at all
    assert " No URLs provided. Please provide at least one URL via the com" in caplog.text
