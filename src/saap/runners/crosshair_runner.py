"""Runner for CrossHair symbolic execution."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any

from saap.runners._base import RunResult


class CrosshairRunner:
    name = "crosshair"

    def is_available(self) -> bool:
        try:
            import crosshair  # noqa: F401

            return True
        except ImportError:
            return False

    def run(self, target: Path, **kwargs: Any) -> RunResult:
        start = time.monotonic()
        errors: list[str] = []
        details: dict[str, Any] = {}

        timeout = kwargs.get("timeout", 60)
        per_condition_timeout = kwargs.get("per_condition_timeout", 10)

        try:
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "crosshair",
                    "check",
                    str(target.resolve()),
                    f"--per_condition_timeout={per_condition_timeout}",
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            details["returncode"] = result.returncode
            details["stdout"] = result.stdout.strip()
            details["stderr"] = result.stderr.strip()

            counterexamples = [
                line
                for line in result.stdout.strip().splitlines()
                if line.strip()
            ]
            details["counterexamples"] = counterexamples

            success = result.returncode == 0 and len(counterexamples) == 0

            if counterexamples:
                summary = f"CrossHair found {len(counterexamples)} counterexample(s)"
            elif success:
                summary = "CrossHair: no counterexamples found"
            else:
                summary = f"CrossHair exited with code {result.returncode}"
                if result.stderr.strip():
                    errors.append(result.stderr.strip())

        except subprocess.TimeoutExpired:
            success = False
            summary = f"CrossHair timed out after {timeout}s"
            errors.append(f"Timeout after {timeout}s")
        except FileNotFoundError:
            success = False
            summary = "CrossHair not found on PATH"
            errors.append("python -m crosshair not found")

        duration = time.monotonic() - start
        return RunResult(
            runner=self.name,
            success=success,
            duration_s=duration,
            summary=summary,
            details=details,
            errors=errors,
        )
