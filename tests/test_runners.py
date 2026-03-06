"""Tests for SAAP runner infrastructure."""

from __future__ import annotations

import pytest

from saap.runners import (
    CrosshairRunner,
    HypothesisRunner,
    IcontractRunner,
    MutmutRunner,
    RunResult,
    Runner,
    get_runners,
)


class TestRunResult:
    def test_creation_minimal(self):
        r = RunResult(runner="test", success=True, duration_s=0.5, summary="ok")
        assert r.runner == "test"
        assert r.success is True
        assert r.duration_s == 0.5
        assert r.summary == "ok"
        assert r.details == {}
        assert r.errors == []

    def test_creation_with_details(self):
        r = RunResult(
            runner="test",
            success=False,
            duration_s=1.2,
            summary="failed",
            details={"key": "value"},
            errors=["something broke"],
        )
        assert r.details == {"key": "value"}
        assert r.errors == ["something broke"]

    def test_default_mutable_fields_independent(self):
        r1 = RunResult(runner="a", success=True, duration_s=0, summary="")
        r2 = RunResult(runner="b", success=True, duration_s=0, summary="")
        r1.details["x"] = 1
        r1.errors.append("e")
        assert r2.details == {}
        assert r2.errors == []


class TestRunnerProtocol:
    @pytest.mark.parametrize(
        "cls",
        [IcontractRunner, HypothesisRunner, CrosshairRunner, MutmutRunner],
    )
    def test_is_runner(self, cls):
        instance = cls()
        assert isinstance(instance, Runner)

    @pytest.mark.parametrize(
        "cls",
        [IcontractRunner, HypothesisRunner, CrosshairRunner, MutmutRunner],
    )
    def test_has_name(self, cls):
        instance = cls()
        assert isinstance(instance.name, str)
        assert len(instance.name) > 0


class TestIsAvailable:
    def test_icontract_available(self):
        assert IcontractRunner().is_available() is True

    def test_hypothesis_available(self):
        assert HypothesisRunner().is_available() is True

    def test_crosshair_available(self):
        assert CrosshairRunner().is_available() is True

    def test_mutmut_available(self):
        runner = MutmutRunner()
        # mutmut is an optional dependency, so it may or may not be installed
        result = runner.is_available()
        assert isinstance(result, bool)


class TestGetRunners:
    def test_single_runner(self):
        runners = get_runners(["icontract"])
        assert len(runners) == 1
        assert runners[0].name == "icontract"

    def test_multiple_runners(self):
        runners = get_runners(["icontract", "hypothesis", "crosshair"])
        assert len(runners) == 3
        names = [r.name for r in runners]
        assert names == ["icontract", "hypothesis", "crosshair"]

    def test_empty_list(self):
        runners = get_runners([])
        assert runners == []

    def test_unknown_runner_raises(self):
        with pytest.raises(ValueError, match="Unknown runner 'nope'"):
            get_runners(["nope"])

    def test_all_runners(self):
        runners = get_runners(["icontract", "hypothesis", "crosshair", "mutmut"])
        assert len(runners) == 4
