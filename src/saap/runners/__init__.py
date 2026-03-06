"""SAAP tool runners."""

from saap.runners._base import Runner, RunResult
from saap.runners.crosshair_runner import CrosshairRunner
from saap.runners.hypothesis_runner import HypothesisRunner
from saap.runners.icontract_runner import IcontractRunner
from saap.runners.mutmut_runner import MutmutRunner

__all__ = [
    "Runner",
    "RunResult",
    "CrosshairRunner",
    "HypothesisRunner",
    "IcontractRunner",
    "MutmutRunner",
    "get_runners",
]

_REGISTRY: dict[str, type] = {
    "icontract": IcontractRunner,
    "hypothesis": HypothesisRunner,
    "crosshair": CrosshairRunner,
    "mutmut": MutmutRunner,
}


def get_runners(names: list[str]) -> list[Runner]:
    runners: list[Runner] = []
    for name in names:
        cls = _REGISTRY.get(name)
        if cls is None:
            raise ValueError(
                f"Unknown runner {name!r}. Available: {sorted(_REGISTRY)}"
            )
        runners.append(cls())
    return runners
