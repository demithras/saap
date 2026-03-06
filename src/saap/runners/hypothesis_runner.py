"""Runner for Hypothesis property-based testing via icontract-hypothesis."""

from __future__ import annotations

import importlib
import inspect
import sys
import time
from pathlib import Path
from typing import Any

from saap.runners._base import RunResult


class HypothesisRunner:
    name = "hypothesis"

    def is_available(self) -> bool:
        try:
            import hypothesis  # noqa: F401
            import icontract_hypothesis  # noqa: F401

            return True
        except ImportError:
            return False

    def run(self, target: Path, **kwargs: Any) -> RunResult:
        start = time.monotonic()
        errors: list[str] = []
        details: dict[str, Any] = {"tested": 0, "passed": 0, "failed": 0}

        module_name = target.stem
        spec_path = str(target.resolve())

        try:
            import icontract
            import icontract_hypothesis

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

            functions = [
                (name, obj)
                for name, obj in inspect.getmembers(module, inspect.isfunction)
                if not name.startswith("_")
                and hasattr(obj, "__preconditions__")
            ]

            details["functions_found"] = len(functions)

            for func_name, func in functions:
                details["tested"] += 1
                try:
                    icontract_hypothesis.test_with_inferred_strategy(func)
                    details["passed"] += 1
                except Exception as exc:
                    details["failed"] += 1
                    errors.append(f"{func_name}: {exc}")

        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            return RunResult(
                runner=self.name,
                success=False,
                duration_s=time.monotonic() - start,
                summary=f"Hypothesis runner error: {exc}",
                details=details,
                errors=errors,
            )

        duration = time.monotonic() - start
        success = details["failed"] == 0
        summary = (
            f"PBT: {details['passed']}/{details['tested']} passed"
            if details["tested"] > 0
            else f"No contracted functions found in {module_name}"
        )

        return RunResult(
            runner=self.name,
            success=success,
            duration_s=duration,
            summary=summary,
            details=details,
            errors=errors,
        )
