"""Runner for icontract contract validation."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from saap.runners._base import RunResult
from saap.runners._loader import load_module_from_path


class IcontractRunner:
    name = "icontract"

    def is_available(self) -> bool:
        try:
            import icontract  # noqa: F401

            return True
        except ImportError:
            return False

    def run(self, target: Path, **kwargs: Any) -> RunResult:
        start = time.monotonic()
        errors: list[str] = []
        details: dict[str, Any] = {}

        module_name = target.stem

        try:
            module = load_module_from_path(target)

            details["module"] = module_name
            details["loaded"] = True

        except Exception as exc:
            exc_type = type(exc).__name__
            errors.append(f"{exc_type}: {exc}")

            is_violation = "ViolationError" in exc_type or "icontract" in exc_type
            details["violation"] = is_violation

            return RunResult(
                runner=self.name,
                success=False,
                duration_s=time.monotonic() - start,
                summary=f"Contract violation in {module_name}: {exc}"
                if is_violation
                else f"Error loading {module_name}: {exc}",
                details=details,
                errors=errors,
            )

        duration = time.monotonic() - start
        return RunResult(
            runner=self.name,
            success=True,
            duration_s=duration,
            summary=f"All contracts satisfied in {module_name}",
            details=details,
        )
