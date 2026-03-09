"""Smoke tests for the SAAP showcase demo.

Structural assertions — validates that inference, dispatch, and the
full demo run produce expected shapes, not exact snapshot values.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from saap.dispatcher import detect_tier
from saap.inference import infer_contracts

MODULES_DIR = Path(__file__).resolve().parent.parent / "examples" / "modules"


class TestBillingInference:
    """billing.py should trigger all 5 inference heuristics."""

    @pytest.fixture()
    def proposals(self):
        return infer_contracts(MODULES_DIR / "billing.py")

    def test_proposal_count(self, proposals):
        assert len(proposals) == 5

    def test_all_heuristic_types_present(self, proposals):
        all_reasoning = " ; ".join(p.reasoning for p in proposals)

        assert "non-negative" in all_reasoning, "name heuristic missing"
        assert "docstring" in all_reasoning, "docstring heuristic missing"
        assert "guard clause" in all_reasoning, "guard clause heuristic missing"
        assert "divisor" in all_reasoning, "division heuristic missing"
        assert "return type" in all_reasoning, "return type heuristic missing"

    def test_every_proposal_has_postcondition(self, proposals):
        for p in proposals:
            assert len(p.postconditions) >= 1, f"{p.function_name} missing postcondition"


class TestInventoryInference:
    """inventory.py should produce proposals for its functions."""

    def test_at_least_two_proposals(self):
        proposals = infer_contracts(MODULES_DIR / "inventory.py")
        assert len(proposals) >= 2


class TestContractedDispatch:
    """billing_contracted.py should be detected at tier >= 2."""

    def test_tier_at_least_2(self):
        tier = detect_tier(MODULES_DIR / "billing_contracted.py")
        assert tier >= 2

    def test_uncontracted_is_tier_1(self):
        tier = detect_tier(MODULES_DIR / "billing.py")
        assert tier == 1


class TestDemoEndToEnd:
    """The full demo script should run without errors."""

    def test_main_returns_zero(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "demo", Path(__file__).resolve().parent.parent / "examples" / "demo.py"
        )
        demo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(demo)
        assert demo.main() == 0
