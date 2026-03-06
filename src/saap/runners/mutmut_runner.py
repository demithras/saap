"""Runner for mutmut mutation testing."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any

from saap.runners._base import RunResult


class MutmutRunner:
    name = "mutmut"

    def is_available(self) -> bool:
        try:
            import mutmut  # noqa: F401

            return True
        except ImportError:
            return False

    def run(self, target: Path, **kwargs: Any) -> RunResult:
        start = time.monotonic()
        errors: list[str] = []
        details: dict[str, Any] = {}

        timeout = kwargs.get("timeout", 300)

        try:
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "mutmut",
                    "run",
                    f"--paths-to-mutate={target.resolve()}",
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            details["returncode"] = result.returncode
            details["stdout"] = result.stdout.strip()
            details["stderr"] = result.stderr.strip()

            stdout = result.stdout
            survived = 0
            killed = 0
            for line in stdout.splitlines():
                lower = line.lower()
                if "survived" in lower:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part.lower() == "survived" and i > 0:
                            try:
                                survived = int(parts[i - 1])
                            except ValueError:
                                pass
                if "killed" in lower:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part.lower() == "killed" and i > 0:
                            try:
                                killed = int(parts[i - 1])
                            except ValueError:
                                pass

            details["survived"] = survived
            details["killed"] = killed
            total = survived + killed
            details["total"] = total

            success = result.returncode == 0 and survived == 0

            if total > 0:
                score = (killed / total) * 100
                details["mutation_score"] = round(score, 1)
                summary = (
                    f"Mutation testing: {killed}/{total} killed "
                    f"({score:.1f}%), {survived} survived"
                )
            else:
                summary = "Mutation testing: no mutants generated"

            if result.returncode != 0 and not total:
                summary = f"mutmut exited with code {result.returncode}"
                if result.stderr.strip():
                    errors.append(result.stderr.strip())

        except subprocess.TimeoutExpired:
            success = False
            summary = f"mutmut timed out after {timeout}s"
            errors.append(f"Timeout after {timeout}s")
        except FileNotFoundError:
            success = False
            summary = "mutmut not found on PATH"
            errors.append("python -m mutmut not found")

        duration = time.monotonic() - start
        return RunResult(
            runner=self.name,
            success=success,
            duration_s=duration,
            summary=summary,
            details=details,
            errors=errors,
        )
