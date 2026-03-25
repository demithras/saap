"""SAAP configuration loader."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_FILENAME = "saap.toml"


@dataclass
class CriticalConfig:
    functions: list[str] = field(default_factory=list)
    modules: list[str] = field(default_factory=list)


@dataclass
class RunnersConfig:
    icontract: bool = True
    hypothesis: bool = True
    crosshair: bool = True
    mutmut: bool = False


@dataclass
class ReportConfig:
    format: str = "console"
    template: str = ""


@dataclass
class SaapConfig:
    default_tier: int = 2
    excluded_paths: list[str] = field(default_factory=list)
    critical: CriticalConfig = field(default_factory=CriticalConfig)
    runners: RunnersConfig = field(default_factory=RunnersConfig)
    report: ReportConfig = field(default_factory=ReportConfig)
    config_path: Path | None = None

    def __post_init__(self):
        if self.default_tier not in (1, 2, 3):
            raise ValueError(
                f"default_tier must be 1, 2, or 3, got {self.default_tier}"
            )


def _find_config(start: Path) -> Path | None:
    current = start.resolve()
    while True:
        candidate = current / CONFIG_FILENAME
        if candidate.is_file():
            return candidate
        parent = current.parent
        if parent == current:
            return None
        current = parent


def _parse_config(data: dict) -> SaapConfig:
    saap = data.get("saap", {})

    critical_raw = saap.get("critical", {})
    critical = CriticalConfig(
        functions=critical_raw.get("functions", []),
        modules=critical_raw.get("modules", []),
    )

    runners_raw = saap.get("runners", {})
    runners = RunnersConfig(
        icontract=runners_raw.get("icontract", True),
        hypothesis=runners_raw.get("hypothesis", True),
        crosshair=runners_raw.get("crosshair", True),
        mutmut=runners_raw.get("mutmut", False),
    )

    report_raw = saap.get("report", {})
    report = ReportConfig(
        format=report_raw.get("format", "console"),
        template=report_raw.get("template", ""),
    )

    return SaapConfig(
        default_tier=saap.get("default_tier", 2),
        excluded_paths=saap.get("excluded_paths", []),
        critical=critical,
        runners=runners,
        report=report,
    )


def load_config(path: Path | None = None) -> SaapConfig:
    if path is None:
        found = _find_config(Path.cwd())
    else:
        found = path if path.is_file() else None

    if found is None:
        return SaapConfig()

    with open(found, "rb") as f:
        data = tomllib.load(f)

    config = _parse_config(data)
    config.config_path = found.resolve()
    return config
