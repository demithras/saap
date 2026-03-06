"""Tests for the SAAP CLI."""

from saap.cli import main


def test_version_flag(capsys):
    try:
        main(["--version"])
    except SystemExit as e:
        assert e.code == 0
    captured = capsys.readouterr()
    assert "saap" in captured.out


def test_no_args():
    assert main([]) == 0
