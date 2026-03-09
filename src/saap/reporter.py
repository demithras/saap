"""SAAP reporting: console, Quarto, and Logseq output channels."""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from saap.config import ReportConfig
from saap.runners._base import RunResult

_TEMPLATES_DIR = Path(__file__).parent / "templates"


@dataclass
class ReportContext:
    """Metadata passed to reporters alongside results."""

    target: Path
    tier: int
    context: str = "manual"
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)


def report_console(results: list[RunResult], ctx: ReportContext) -> str:
    """Rich-formatted console summary. Returns the rendered string."""
    lines: list[str] = []
    sep = "=" * 60
    thin = "-" * 60

    lines.append(sep)
    lines.append("SAAP Verification Report")
    lines.append(thin)
    lines.append(f"Target  : {ctx.target}")
    lines.append(f"Tier    : {ctx.tier}")
    lines.append(f"Context : {ctx.context}")
    lines.append(f"Time    : {ctx.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(sep)

    if not results:
        lines.append("  (no runners executed)")
        lines.append(sep)
        return "\n".join(lines)

    for r in results:
        status = "\u2713" if r.success else "\u2717"
        lines.append(f"  [{status}] {r.runner:<20}  {r.duration_s:.2f}s")
        lines.append(f"       {r.summary}")
        if r.errors:
            for err in r.errors:
                lines.append(f"       ! {err}")

    lines.append(thin)
    total_duration = sum(r.duration_s for r in results)
    all_passed = all(r.success for r in results)
    verdict = "PASS" if all_passed else "FAIL"
    lines.append(f"Overall : {verdict}  |  Total duration: {total_duration:.2f}s")
    lines.append(sep)

    return "\n".join(lines)


def _build_summary_table(results: list[RunResult]) -> str:
    """Build a markdown pipe table summarising all runner results."""
    header = "| Runner | Status | Duration (s) | Summary |"
    divider = "|--------|--------|-------------|---------|"
    rows = [header, divider]
    for r in results:
        status = "PASS" if r.success else "FAIL"
        rows.append(
            f"| {r.runner} | {status} | {r.duration_s:.2f} | {r.summary} |"
        )
    return "\n".join(rows)


def _build_runner_details(results: list[RunResult]) -> str:
    """Build per-runner detail sections in Quarto markdown."""
    sections: list[str] = []
    for r in results:
        status = "PASS" if r.success else "FAIL"
        block: list[str] = []
        block.append(f"### {r.runner} ({status})")
        block.append("")
        block.append(f"**Duration**: {r.duration_s:.2f}s")
        block.append("")
        block.append(f"**Summary**: {r.summary}")

        if r.errors:
            block.append("")
            block.append("**Errors**:")
            block.append("")
            for err in r.errors:
                block.append(f"- {err}")

        if r.details:
            block.append("")
            block.append("**Metrics**:")
            block.append("")
            for key, value in r.details.items():
                block.append(f"- **{key}**: {value}")

        sections.append("\n".join(block))

    return "\n\n".join(sections)


def report_quarto(
    results: list[RunResult],
    ctx: ReportContext,
    template: Path | None = None,
) -> str:
    """Generate a Quarto markdown document (.qmd) from results."""
    if template is not None and template.exists():
        raw = template.read_text(encoding="utf-8")
    else:
        default = _TEMPLATES_DIR / "default.qmd"
        raw = default.read_text(encoding="utf-8")

    total_duration = sum(r.duration_s for r in results)
    all_passed = all(r.success for r in results) if results else True
    verdict_word = "PASS" if all_passed else "FAIL"

    if results:
        verdict = (
            f"**{verdict_word}** — "
            f"{sum(1 for r in results if r.success)}/{len(results)} runners passed "
            f"in {total_duration:.2f}s total."
        )
    else:
        verdict = "No runners were executed."

    summary_table = _build_summary_table(results) if results else "_No runners executed._"
    runner_details = _build_runner_details(results) if results else "_No runner details available._"

    substitutions: dict[str, str] = {
        "TARGET": str(ctx.target),
        "TIER": str(ctx.tier),
        "CONTEXT": ctx.context,
        "DATE": ctx.timestamp.strftime("%Y-%m-%d"),
        "SUMMARY_TABLE": summary_table,
        "RUNNER_DETAILS": runner_details,
        "VERDICT": verdict,
    }

    result = raw
    for placeholder, value in substitutions.items():
        result = result.replace(f"{{{placeholder}}}", value)

    return result


def report_logseq(results: list[RunResult], ctx: ReportContext) -> str:
    """Generate a Logseq-compatible markdown block."""
    lines: list[str] = []
    ts = ctx.timestamp.strftime("%Y-%m-%d %H:%M")

    lines.append(f"- SAAP Run: {ctx.target} (Tier {ctx.tier}) #saap")

    for r in results:
        status = "\u2713" if r.success else "\u2717"
        lines.append(f"  - Runner: {r.runner} \u2014 {status} ({r.duration_s:.2f}s)")
        lines.append(f"    - {r.summary}")
        if r.errors:
            for err in r.errors:
                lines.append(f"    - ERROR: {err}")

    total_duration = sum(r.duration_s for r in results)
    all_passed = all(r.success for r in results) if results else True
    verdict = "PASS" if all_passed else "FAIL"
    lines.append(f"  - Overall: {verdict} | {total_duration:.2f}s | {ts}")

    return "\n".join(lines)


def report(
    results: list[RunResult],
    ctx: ReportContext,
    config: ReportConfig | None = None,
) -> str:
    """Main entry point: dispatch to the appropriate channel based on config."""
    if config is None:
        config = ReportConfig()

    if config.format == "quarto":
        template = Path(config.template) if config.template else None
        return report_quarto(results, ctx, template)
    elif config.format == "logseq":
        return report_logseq(results, ctx)
    else:
        return report_console(results, ctx)
