"""Tests for the smart dispatcher."""

from __future__ import annotations

from pathlib import Path

import pytest

from saap.config import CriticalConfig, RunnersConfig, SaapConfig
from saap.dispatcher import detect_tier, dispatch


# ---------------------------------------------------------------------------
# Fixtures: sample source code
# ---------------------------------------------------------------------------

PLAIN_SOURCE = """\
def add(a, b):
    return a + b
"""

CONTRACTED_SOURCE = """\
from icontract import require, ensure

@require(lambda x: x >= 0)
@ensure(lambda result: result >= 0)
def sqrt(x):
    return x ** 0.5
"""

C_EXTENSION_SOURCE = """\
import ctypes
from icontract import require

@require(lambda ptr: ptr is not None)
def read_memory(ptr):
    return ctypes.string_at(ptr, 8)
"""

CFFI_SOURCE = """\
import cffi
from icontract import ensure

@ensure(lambda result: result is not None)
def build_ffi():
    ffi = cffi.FFI()
    return ffi
"""

CRITICAL_FUNC_SOURCE = """\
from icontract import require

@require(lambda amount: amount > 0)
def process_payment(amount):
    return amount
"""


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return p


# ---------------------------------------------------------------------------
# detect_tier: context-based rules
# ---------------------------------------------------------------------------

class TestContextRules:
    def test_precommit_caps_at_tier1(self, tmp_path: Path):
        src = _write(tmp_path, "mod.py", CONTRACTED_SOURCE)
        assert detect_tier(src, context="pre-commit") == 1

    def test_pr_caps_at_tier2(self, tmp_path: Path):
        src = _write(tmp_path, "mod.py", C_EXTENSION_SOURCE)
        # Would be tier 3 without cap, but PR caps at 2
        assert detect_tier(src, context="pr") == 2

    def test_audit_forces_tier3(self, tmp_path: Path):
        src = _write(tmp_path, "mod.py", PLAIN_SOURCE)
        assert detect_tier(src, context="audit") == 3

    def test_manual_uses_detection(self, tmp_path: Path):
        src = _write(tmp_path, "mod.py", CONTRACTED_SOURCE)
        assert detect_tier(src, context="manual") == 2  # default_tier


# ---------------------------------------------------------------------------
# detect_tier: AST analysis
# ---------------------------------------------------------------------------

class TestASTDetection:
    def test_no_contracts_gets_tier1(self, tmp_path: Path):
        src = _write(tmp_path, "mod.py", PLAIN_SOURCE)
        assert detect_tier(src) == 1

    def test_contracts_get_default_tier(self, tmp_path: Path):
        src = _write(tmp_path, "mod.py", CONTRACTED_SOURCE)
        assert detect_tier(src) == 2

    def test_ctypes_import_bumps_to_tier3(self, tmp_path: Path):
        src = _write(tmp_path, "mod.py", C_EXTENSION_SOURCE)
        assert detect_tier(src) == 3

    def test_cffi_import_bumps_to_tier3(self, tmp_path: Path):
        src = _write(tmp_path, "mod.py", CFFI_SOURCE)
        assert detect_tier(src) == 3


# ---------------------------------------------------------------------------
# detect_tier: critical functions / modules
# ---------------------------------------------------------------------------

class TestCriticalDetection:
    def test_critical_function_forces_tier3(self, tmp_path: Path):
        src = _write(tmp_path, "mod.py", CRITICAL_FUNC_SOURCE)
        config = SaapConfig(
            critical=CriticalConfig(functions=["process_payment"]),
        )
        assert detect_tier(src, config=config) == 3

    def test_critical_module_forces_tier3(self, tmp_path: Path):
        src = _write(tmp_path, "payments/core.py", CONTRACTED_SOURCE)
        config = SaapConfig(
            critical=CriticalConfig(modules=["payments"]),
        )
        assert detect_tier(src, config=config) == 3

    def test_non_critical_stays_default(self, tmp_path: Path):
        src = _write(tmp_path, "utils.py", CONTRACTED_SOURCE)
        config = SaapConfig(
            critical=CriticalConfig(functions=["process_payment"]),
        )
        assert detect_tier(src, config=config) == 2


# ---------------------------------------------------------------------------
# dispatch: runner lists
# ---------------------------------------------------------------------------

class TestDispatch:
    def test_tier1_returns_icontract_only(self, tmp_path: Path):
        src = _write(tmp_path, "mod.py", PLAIN_SOURCE)
        assert dispatch(src) == ["icontract"]

    def test_tier2_returns_icontract_and_hypothesis(self, tmp_path: Path):
        src = _write(tmp_path, "mod.py", CONTRACTED_SOURCE)
        assert dispatch(src) == ["icontract", "hypothesis"]

    def test_tier3_returns_all_enabled(self, tmp_path: Path):
        src = _write(tmp_path, "mod.py", C_EXTENSION_SOURCE)
        # mutmut is disabled by default
        assert dispatch(src) == ["icontract", "hypothesis", "crosshair"]

    def test_tier3_with_mutmut_enabled(self, tmp_path: Path):
        src = _write(tmp_path, "mod.py", C_EXTENSION_SOURCE)
        config = SaapConfig(runners=RunnersConfig(mutmut=True))
        assert dispatch(src, config=config) == [
            "icontract", "hypothesis", "crosshair", "mutmut",
        ]

    def test_disabled_runner_excluded(self, tmp_path: Path):
        src = _write(tmp_path, "mod.py", CONTRACTED_SOURCE)
        config = SaapConfig(runners=RunnersConfig(hypothesis=False))
        assert dispatch(src, config=config) == ["icontract"]

    def test_audit_context_with_defaults(self, tmp_path: Path):
        src = _write(tmp_path, "mod.py", PLAIN_SOURCE)
        result = dispatch(src, context="audit")
        # Audit forces tier 3; mutmut off by default
        assert result == ["icontract", "hypothesis", "crosshair"]
