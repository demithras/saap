"""Base types for SAAP runners."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@dataclass
class RunResult:
    runner: str
    success: bool
    duration_s: float
    summary: str
    details: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


@runtime_checkable
class Runner(Protocol):
    name: str

    def run(self, target: Path, **kwargs: Any) -> RunResult: ...

    def is_available(self) -> bool: ...
