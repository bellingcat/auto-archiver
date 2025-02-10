import sys
import pytest

from auto_archiver.__main__ import main

@pytest.fixture
def orchestration_file(tmp_path):
    return (tmp_path / "example_orch.yaml").as_posix()

@pytest.fixture
def autoarchiver(tmp_path, monkeypatch):

    def _autoarchiver(args=["--config", "example_orch.yaml"]):
        # change dir to tmp_path
        monkeypatch.chdir(tmp_path)
        with monkeypatch.context() as m:
            m.setattr(sys, "argv", ["auto-archiver"] + args)
            return main()
    
    return _autoarchiver


def test_run_auto_archiver_no_args(caplog, autoarchiver):
    with pytest.raises(SystemExit):
        autoarchiver([])

    assert "provide at least one URL via the command line, or set up an alternative feeder" in caplog.text


def test_run_auto_archiver_invalid_file(caplog, autoarchiver, monkeypatch):
    # exec 'auto-archiver' on the command lin
    with pytest.raises(SystemExit):
        autoarchiver()

    assert "Make sure the file exists and try again, or run without th" in caplog.text