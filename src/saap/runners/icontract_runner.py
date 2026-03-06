"""Runner for icontract contract validation."""

from __future__ import annotations

import importlib
import sys
import time
from pathlib import Path
from typing import Any

from saap.runners._base import RunResult


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
        spec_path = str(target.resolve())

        try:
            spec = importlib.util.spec_from_file_location(module_name, spec_path)
            if spec is None or spec.loader is None:
                return RunResult(
                    runner=self.name,
                    success=False,
                    duration_s=time.monotonic() - start,
                    summary=f"Could not load module spec from {target}",
                    errors=[f"Invalid module path: {target}"],
                )

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

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
