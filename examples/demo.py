#!/usr/bin/env python3
"""SAAP Golden Chain Demo — 4 stages of contract-based verification.

Usage:
    python examples/demo.py

Runs inference, diff, dispatch, and reporting on example modules
to demonstrate the full SAAP pipeline end-to-end.
"""

from __future__ import annotations

import datetime
import sys
from pathlib import Path

# Ensure the src directory is importable when running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from saap.dispatcher import detect_tier, dispatch
from saap.inference import ContractProposal, format_diff, infer_contracts
from saap.reporter import ReportContext, report_console, report_logseq
from saap.runners._base import RunResult

MODULES_DIR = Path(__file__).resolve().parent / "modules"

SECTION = "=" * 60
THIN = "-" * 60


def stage_inference() -> dict[str, list[ContractProposal]]:
    """Stage 1: Infer contracts from un-contracted modules."""
    print(f"\n{SECTION}")
    print("Stage 1: INFERENCE")
    print(SECTION)

    results: dict[str, list[ContractProposal]] = {}
    for name in ("billing", "inventory"):
        source = MODULES_DIR / f"{name}.py"
        proposals = infer_contracts(source)
        results[name] = proposals
        print(f"\n  {source.name}: {len(proposals)} proposals")
        for p in proposals:
            heuristics = []
            if any("guard" in r for r in p.reasoning.split(";")):
                heuristics.append("guard")
            if any("docstring" in r for r in p.reasoning.split(";")):
                heuristics.append("docstring")
            if any("non-negative" in r for r in p.reasoning.split(";")):
                heuristics.append("name")
            if any("divisor" in r for r in p.reasoning.split(";")):
                heuristics.append("division")
            if any("return type" in r for r in p.reasoning.split(";")):
                heuristics.append("return_type")
            print(
                f"    {p.function_name}: "
                f"{len(p.preconditions)} pre + {len(p.postconditions)} post "
                f"(confidence {p.confidence}) [{', '.join(heuristics)}]"
            )

    return results


def stage_diff(proposals_by_module: dict[str, list[ContractProposal]]) -> None:
    """Stage 2: Show unified diffs of proposed decorators."""
    print(f"\n{SECTION}")
    print("Stage 2: DIFF")
    print(SECTION)

    for name, proposals in proposals_by_module.items():
        source = MODULES_DIR / f"{name}.py"
        diff = format_diff(proposals, source)
        print(f"\n  --- {source.name} ---")
        for line in diff.splitlines():
            print(f"  {line}")


def stage_dispatch() -> None:
    """Stage 3: Demonstrate tier detection and dispatch."""
    print(f"\n{SECTION}")
    print("Stage 3: DISPATCH")
    print(SECTION)

    contracted = MODULES_DIR / "billing_contracted.py"
    uncontracted = MODULES_DIR / "billing.py"

    scenarios = [
        (uncontracted, "manual"),
        (contracted, "manual"),
        (contracted, "pre-commit"),
        (contracted, "audit"),
    ]

    for source, context in scenarios:
        tier = detect_tier(source, context)
        runners = dispatch(source, context)
        print(f"\n  {source.name} ({context}):")
        print(f"    Tier {tier} -> runners: {runners}")


def stage_report() -> None:
    """Stage 4: Generate reports from synthetic RunResults."""
    print(f"\n{SECTION}")
    print("Stage 4: REPORT")
    print(SECTION)

    target = MODULES_DIR / "billing_contracted.py"
    ctx = ReportContext(
        target=target,
        tier=2,
        context="manual",
        timestamp=datetime.datetime(2026, 3, 9, 14, 0, 0),
    )

    results = [
        RunResult(
            runner="icontract",
            success=True,
            duration_s=0.42,
            summary="5 functions checked, all contracts hold",
        ),
        RunResult(
            runner="hypothesis",
            success=True,
            duration_s=2.15,
            summary="Generated 500 test cases, 0 failures",
            details={"test_cases": 500, "failures": 0},
        ),
    ]

    print("\n  --- Console Report ---")
    console = report_console(results, ctx)
    for line in console.splitlines():
        print(f"  {line}")

    print(f"\n  --- Logseq Report ---")
    logseq = report_logseq(results, ctx)
    for line in logseq.splitlines():
        print(f"  {line}")


def main() -> int:
    """Run all 4 stages of the golden chain demo."""
    proposals = stage_inference()
    stage_diff(proposals)
    stage_dispatch()
    stage_report()

    print(f"\n{SECTION}")
    print("Demo complete.")
    print(SECTION)
    return 0


if __name__ == "__main__":
    sys.exit(main())
