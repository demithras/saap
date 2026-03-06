"""Tests for saap.config module."""

from __future__ import annotations

from pathlib import Path

import pytest

from saap.config import SaapConfig, load_config

FULL_CONFIG = """\
[saap]
default_tier = 3
excluded_paths = ["migrations/", "vendor/"]

[saap.critical]
functions = ["process_payment", "authenticate"]
modules = ["auth", "billing"]

[saap.runners]
icontract = true
hypothesis = true
crosshair = false
mutmut = true

[saap.report]
format = "quarto"
template = "custom.qmd"
"""

PARTIAL_CONFIG = """\
[saap]
default_tier = 1
"""


class TestLoadValidConfig:
    def test_full_config(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "saap.toml"
        cfg_file.write_text(FULL_CONFIG)

        config = load_config(cfg_file)

        assert config.default_tier == 3
        assert config.excluded_paths == ["migrations/", "vendor/"]
        assert config.critical.functions == ["process_payment", "authenticate"]
        assert config.critical.modules == ["auth", "billing"]
        assert config.runners.icontract is True
        assert config.runners.crosshair is False
        assert config.runners.mutmut is True
        assert config.report.format == "quarto"
        assert config.report.template == "custom.qmd"
        assert config.config_path == cfg_file.resolve()

    def test_config_path_is_set(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "saap.toml"
        cfg_file.write_text(FULL_CONFIG)

        config = load_config(cfg_file)
        assert config.config_path is not None
        assert config.config_path.name == "saap.toml"


class TestDefaults:
    def test_defaults_when_no_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        config = load_config()

        assert config.default_tier == 2
        assert config.excluded_paths == []
        assert config.critical.functions == []
        assert config.critical.modules == []
        assert config.runners.icontract is True
        assert config.runners.hypothesis is True
        assert config.runners.crosshair is True
        assert config.runners.mutmut is False
        assert config.report.format == "console"
        assert config.report.template == ""
        assert config.config_path is None

    def test_defaults_when_explicit_missing_path(self, tmp_path: Path) -> None:
        config = load_config(tmp_path / "nonexistent.toml")
        assert config.config_path is None
        assert config.default_tier == 2


class TestPartialConfig:
    def test_only_saap_section(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "saap.toml"
        cfg_file.write_text(PARTIAL_CONFIG)

        config = load_config(cfg_file)

        assert config.default_tier == 1
        # Everything else should be defaults
        assert config.excluded_paths == []
        assert config.critical.functions == []
        assert config.runners.mutmut is False
        assert config.report.format == "console"

    def test_empty_file(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "saap.toml"
        cfg_file.write_text("")

        config = load_config(cfg_file)
        assert config.default_tier == 2


class TestDirectorySearch:
    def test_finds_config_in_parent(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        cfg_file = tmp_path / "saap.toml"
        cfg_file.write_text(PARTIAL_CONFIG)

        child = tmp_path / "src" / "deep"
        child.mkdir(parents=True)
        monkeypatch.chdir(child)

        config = load_config()

        assert config.default_tier == 1
        assert config.config_path == cfg_file.resolve()

    def test_finds_config_in_cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        cfg_file = tmp_path / "saap.toml"
        cfg_file.write_text(FULL_CONFIG)
        monkeypatch.chdir(tmp_path)

        config = load_config()
        assert config.default_tier == 3

    def test_no_config_found_at_root(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        config = load_config()
        assert config.config_path is None
