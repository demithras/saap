"""Tests for saap.reporter module."""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from saap.config import ReportConfig
from saap.reporter import ReportContext, report, report_console, report_logseq, report_quarto
from saap.runners._base import RunResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def target_path() -> Path:
    return Path("src/mymodule.py")


@pytest.fixture()
def ctx(target_path: Path) -> ReportContext:
    return ReportContext(
        target=target_path,
        tier=2,
        context="manual",
        timestamp=datetime.datetime(2026, 3, 9, 12, 0, 0),
    )


@pytest.fixture()
def passing_result() -> RunResult:
    return RunResult(
        runner="icontract",
        success=True,
        duration_s=0.42,
        summary="All contracts satisfied",
        details={"checks": 10},
    )


@pytest.fixture()
def failing_result() -> RunResult:
    return RunResult(
        runner="hypothesis",
        success=False,
        duration_s=1.23,
        summary="Counterexample found",
        details={"counterexamples": 1},
        errors=["AssertionError: x=-1 violated invariant"],
    )


@pytest.fixture()
def mixed_results(passing_result: RunResult, failing_result: RunResult) -> list[RunResult]:
    return [passing_result, failing_result]


@pytest.fixture()
def all_fail_results() -> list[RunResult]:
    return [
        RunResult(
            runner="icontract",
            success=False,
            duration_s=0.1,
            summary="Contract violated",
            errors=["ViolationError: pre-condition failed"],
        ),
        RunResult(
            runner="hypothesis",
            success=False,
            duration_s=2.5,
            summary="Multiple counterexamples found",
            errors=["Error A", "Error B"],
        ),
    ]


# ---------------------------------------------------------------------------
# report_console
# ---------------------------------------------------------------------------


class TestReportConsole:
    def test_contains_target(self, mixed_results: list[RunResult], ctx: ReportContext) -> None:
        output = report_console(mixed_results, ctx)
        assert "src/mymodule.py" in output

    def test_contains_tier(self, mixed_results: list[RunResult], ctx: ReportContext) -> None:
        output = report_console(mixed_results, ctx)
        assert "2" in output

    def test_pass_mark_for_passing_runner(
        self, mixed_results: list[RunResult], ctx: ReportContext
    ) -> None:
        output = report_console(mixed_results, ctx)
        assert "\u2713" in output  # ✓

    def test_fail_mark_for_failing_runner(
        self, mixed_results: list[RunResult], ctx: ReportContext
    ) -> None:
        output = report_console(mixed_results, ctx)
        assert "\u2717" in output  # ✗

    def test_overall_fail_when_any_fail(
        self, mixed_results: list[RunResult], ctx: ReportContext
    ) -> None:
        output = report_console(mixed_results, ctx)
        assert "FAIL" in output

    def test_overall_pass_when_all_pass(
        self, passing_result: RunResult, ctx: ReportContext
    ) -> None:
        output = report_console([passing_result], ctx)
        assert "PASS" in output

    def test_errors_included(self, mixed_results: list[RunResult], ctx: ReportContext) -> None:
        output = report_console(mixed_results, ctx)
        assert "AssertionError: x=-1 violated invariant" in output

    def test_duration_shown(self, mixed_results: list[RunResult], ctx: ReportContext) -> None:
        output = report_console(mixed_results, ctx)
        assert "0.42" in output
        assert "1.23" in output

    def test_empty_results(self, ctx: ReportContext) -> None:
        output = report_console([], ctx)
        assert "no runners executed" in output.lower()

    def test_all_failures_with_errors(
        self, all_fail_results: list[RunResult], ctx: ReportContext
    ) -> None:
        output = report_console(all_fail_results, ctx)
        assert "FAIL" in output
        assert "ViolationError: pre-condition failed" in output
        assert "Error A" in output
        assert "Error B" in output
        assert "icontract" in output
        assert "hypothesis" in output

    def test_returns_string(self, mixed_results: list[RunResult], ctx: ReportContext) -> None:
        output = report_console(mixed_results, ctx)
        assert isinstance(output, str)


# ---------------------------------------------------------------------------
# report_quarto
# ---------------------------------------------------------------------------


class TestReportQuarto:
    def test_yaml_front_matter(self, mixed_results: list[RunResult], ctx: ReportContext) -> None:
        output = report_quarto(mixed_results, ctx)
        assert "---" in output
        assert "title:" in output
        assert "format:" in output

    def test_target_in_title(self, mixed_results: list[RunResult], ctx: ReportContext) -> None:
        output = report_quarto(mixed_results, ctx)
        assert "src/mymodule.py" in output

    def test_date_substituted(self, mixed_results: list[RunResult], ctx: ReportContext) -> None:
        output = report_quarto(mixed_results, ctx)
        assert "2026-03-09" in output

    def test_summary_table_present(self, mixed_results: list[RunResult], ctx: ReportContext) -> None:
        output = report_quarto(mixed_results, ctx)
        assert "| Runner |" in output
        assert "| icontract |" in output
        assert "| hypothesis |" in output

    def test_runner_details_section(self, mixed_results: list[RunResult], ctx: ReportContext) -> None:
        output = report_quarto(mixed_results, ctx)
        assert "### icontract" in output
        assert "### hypothesis" in output

    def test_verdict_pass(self, passing_result: RunResult, ctx: ReportContext) -> None:
        output = report_quarto([passing_result], ctx)
        assert "PASS" in output

    def test_verdict_fail(self, mixed_results: list[RunResult], ctx: ReportContext) -> None:
        output = report_quarto(mixed_results, ctx)
        assert "FAIL" in output

    def test_details_dict_rendered(self, mixed_results: list[RunResult], ctx: ReportContext) -> None:
        output = report_quarto(mixed_results, ctx)
        assert "checks" in output
        assert "counterexamples" in output

    def test_custom_template(
        self, tmp_path: Path, mixed_results: list[RunResult], ctx: ReportContext
    ) -> None:
        template = tmp_path / "custom.qmd"
        template.write_text(
            "# {TARGET} - Tier {TIER}\n{SUMMARY_TABLE}\n{VERDICT}\n",
            encoding="utf-8",
        )
        output = report_quarto(mixed_results, ctx, template=template)
        assert "src/mymodule.py" in output
        assert "2" in output
        assert "| Runner |" in output
        assert "FAIL" in output

    def test_missing_template_falls_back_to_default(
        self, tmp_path: Path, mixed_results: list[RunResult], ctx: ReportContext
    ) -> None:
        missing = tmp_path / "nonexistent.qmd"
        # Should not raise; falls back to built-in default
        output = report_quarto(mixed_results, ctx, template=missing)
        assert "SAAP" in output

    def test_no_placeholders_remain(
        self, mixed_results: list[RunResult], ctx: ReportContext
    ) -> None:
        output = report_quarto(mixed_results, ctx)
        # None of the substitution keys should remain verbatim
        for placeholder in ("{TARGET}", "{TIER}", "{DATE}", "{SUMMARY_TABLE}", "{RUNNER_DETAILS}", "{VERDICT}", "{CONTEXT}"):
            assert placeholder not in output

    def test_empty_results(self, ctx: ReportContext) -> None:
        output = report_quarto([], ctx)
        assert isinstance(output, str)
        assert "No runners" in output or "no runners" in output.lower()


# ---------------------------------------------------------------------------
# report_logseq
# ---------------------------------------------------------------------------


class TestReportLogseq:
    def test_starts_with_saap_run(self, mixed_results: list[RunResult], ctx: ReportContext) -> None:
        output = report_logseq(mixed_results, ctx)
        assert output.startswith("- SAAP Run:")

    def test_contains_target(self, mixed_results: list[RunResult], ctx: ReportContext) -> None:
        output = report_logseq(mixed_results, ctx)
        assert "src/mymodule.py" in output

    def test_contains_tier(self, mixed_results: list[RunResult], ctx: ReportContext) -> None:
        output = report_logseq(mixed_results, ctx)
        assert "Tier 2" in output

    def test_tagged_saap(self, mixed_results: list[RunResult], ctx: ReportContext) -> None:
        output = report_logseq(mixed_results, ctx)
        assert "#saap" in output

    def test_runner_bullets(self, mixed_results: list[RunResult], ctx: ReportContext) -> None:
        output = report_logseq(mixed_results, ctx)
        assert "icontract" in output
        assert "hypothesis" in output

    def test_pass_mark(self, passing_result: RunResult, ctx: ReportContext) -> None:
        output = report_logseq([passing_result], ctx)
        assert "\u2713" in output

    def test_fail_mark(self, failing_result: RunResult, ctx: ReportContext) -> None:
        output = report_logseq([failing_result], ctx)
        assert "\u2717" in output

    def test_overall_verdict_line(self, mixed_results: list[RunResult], ctx: ReportContext) -> None:
        output = report_logseq(mixed_results, ctx)
        assert "Overall:" in output
        assert "FAIL" in output

    def test_errors_in_output(self, failing_result: RunResult, ctx: ReportContext) -> None:
        output = report_logseq([failing_result], ctx)
        assert "AssertionError" in output

    def test_indented_bullets(self, mixed_results: list[RunResult], ctx: ReportContext) -> None:
        lines = report_logseq(mixed_results, ctx).splitlines()
        # At least one line must be indented (runner-level bullets)
        indented = [l for l in lines if l.startswith("  -")]
        assert len(indented) > 0

    def test_empty_results(self, ctx: ReportContext) -> None:
        output = report_logseq([], ctx)
        assert isinstance(output, str)
        assert "#saap" in output
        assert "Overall:" in output

    def test_all_failures(
        self, all_fail_results: list[RunResult], ctx: ReportContext
    ) -> None:
        output = report_logseq(all_fail_results, ctx)
        assert "FAIL" in output
        assert "ViolationError" in output
        assert "Error A" in output


# ---------------------------------------------------------------------------
# report() dispatcher
# ---------------------------------------------------------------------------


class TestReportDispatcher:
    def test_default_is_console(self, mixed_results: list[RunResult], ctx: ReportContext) -> None:
        output = report(mixed_results, ctx)
        # Console output has separator lines
        assert "=" * 10 in output

    def test_console_explicit(self, mixed_results: list[RunResult], ctx: ReportContext) -> None:
        config = ReportConfig(format="console")
        output = report(mixed_results, ctx, config)
        assert "=" * 10 in output

    def test_quarto_dispatch(self, mixed_results: list[RunResult], ctx: ReportContext) -> None:
        config = ReportConfig(format="quarto")
        output = report(mixed_results, ctx, config)
        assert "---" in output
        assert "title:" in output

    def test_logseq_dispatch(self, mixed_results: list[RunResult], ctx: ReportContext) -> None:
        config = ReportConfig(format="logseq")
        output = report(mixed_results, ctx, config)
        assert output.startswith("- SAAP Run:")
        assert "#saap" in output

    def test_none_config_uses_defaults(
        self, mixed_results: list[RunResult], ctx: ReportContext
    ) -> None:
        output = report(mixed_results, ctx, config=None)
        assert isinstance(output, str)
        assert len(output) > 0

    def test_quarto_with_template_path(
        self, tmp_path: Path, mixed_results: list[RunResult], ctx: ReportContext
    ) -> None:
        template = tmp_path / "t.qmd"
        template.write_text("Target={TARGET} Verdict={VERDICT}", encoding="utf-8")
        config = ReportConfig(format="quarto", template=str(template))
        output = report(mixed_results, ctx, config)
        assert "src/mymodule.py" in output
        assert "FAIL" in output

    def test_unknown_format_falls_back_to_console(
        self, mixed_results: list[RunResult], ctx: ReportContext
    ) -> None:
        config = ReportConfig(format="unknown_format")
        output = report(mixed_results, ctx, config)
        # Falls through the else branch → console
        assert "SAAP Verification Report" in output
