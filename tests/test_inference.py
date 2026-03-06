"""Tests for the contract inference engine."""

from pathlib import Path
from textwrap import dedent

from saap.inference import (
    ContractProposal,
    apply_contracts,
    format_diff,
    infer_contracts,
)


def _write_source(tmp_path: Path, code: str) -> Path:
    p = tmp_path / "example.py"
    p.write_text(dedent(code))
    return p


def test_non_negative_from_type_hint_and_name(tmp_path):
    src = _write_source(tmp_path, """\
        def grow(age: int, name: str) -> None:
            pass
    """)
    proposals = infer_contracts(src)
    assert len(proposals) == 1
    p = proposals[0]
    assert p.function_name == "grow"
    assert "lambda age: age >= 0" in p.preconditions
    # 'name' is str, not a known non-negative quantity -> no precondition
    assert not any("name" in c for c in p.preconditions)


def test_divisor_param(tmp_path):
    src = _write_source(tmp_path, """\
        def divide(a: float, divisor: float) -> float:
            return a / divisor
    """)
    proposals = infer_contracts(src)
    assert len(proposals) == 1
    assert "lambda divisor: divisor != 0" in proposals[0].preconditions


def test_division_in_body(tmp_path):
    src = _write_source(tmp_path, """\
        def ratio(x: float, y: float) -> float:
            return x / y
    """)
    proposals = infer_contracts(src)
    assert len(proposals) == 1
    assert "lambda y: y != 0" in proposals[0].preconditions


def test_optional_param_skipped(tmp_path):
    src = _write_source(tmp_path, """\
        from typing import Optional
        def fetch(url: str, timeout: Optional[int] = None) -> str:
            return ""
    """)
    proposals = infer_contracts(src)
    # Should only have postcondition for return type, no precondition on timeout
    assert len(proposals) == 1
    assert not any("timeout" in c for c in proposals[0].preconditions)


def test_guard_clause_raise(tmp_path):
    src = _write_source(tmp_path, """\
        def sqrt(x: float) -> float:
            if x < 0:
                raise ValueError("negative")
            return x ** 0.5
    """)
    proposals = infer_contracts(src)
    assert len(proposals) == 1
    assert "lambda x: x >= 0" in proposals[0].preconditions


def test_guard_clause_not_equal(tmp_path):
    src = _write_source(tmp_path, """\
        def invert(x: float) -> float:
            if x == 0:
                raise ValueError("zero")
            return 1 / x
    """)
    proposals = infer_contracts(src)
    assert len(proposals) == 1
    assert "lambda x: x != 0" in proposals[0].preconditions


def test_docstring_must_be_positive(tmp_path):
    src = _write_source(tmp_path, """\
        def allocate(n: int) -> list:
            \"\"\"Allocate a buffer. n must be positive.\"\"\"
            return [0] * n
    """)
    proposals = infer_contracts(src)
    assert len(proposals) == 1
    assert "lambda n: n > 0" in proposals[0].preconditions


def test_docstring_non_empty(tmp_path):
    src = _write_source(tmp_path, """\
        def first(items: list) -> object:
            \"\"\"Return the first element. items must be non-empty.\"\"\"
            return items[0]
    """)
    proposals = infer_contracts(src)
    assert len(proposals) == 1
    assert "lambda items: len(items) > 0" in proposals[0].preconditions


def test_return_type_postcondition(tmp_path):
    src = _write_source(tmp_path, """\
        def compute(x: float) -> int:
            return int(x)
    """)
    proposals = infer_contracts(src)
    assert len(proposals) == 1
    assert "lambda result: isinstance(result, int)" in proposals[0].postconditions


def test_no_proposals_for_plain_function(tmp_path):
    src = _write_source(tmp_path, """\
        def greet(message):
            print(message)
    """)
    proposals = infer_contracts(src)
    assert proposals == []


def test_path_param_skipped(tmp_path):
    src = _write_source(tmp_path, """\
        def read_file(path: str) -> str:
            return open(path).read()
    """)
    proposals = infer_contracts(src)
    # Should have postcondition but no precondition on path
    assert len(proposals) == 1
    assert not any("path" in c for c in proposals[0].preconditions)


def test_self_param_skipped(tmp_path):
    src = _write_source(tmp_path, """\
        class Foo:
            def bar(self, count: int) -> None:
                pass
    """)
    proposals = infer_contracts(src)
    assert len(proposals) == 1
    assert not any("self" in c for c in proposals[0].preconditions)


def test_format_diff_produces_unified_diff(tmp_path):
    src = _write_source(tmp_path, """\
        def grow(age: int) -> None:
            pass
    """)
    proposals = infer_contracts(src)
    diff = format_diff(proposals, src)
    assert diff.startswith("---")
    assert "+++" in diff
    assert "@icontract.require" in diff


def test_apply_contracts_adds_import_and_decorators(tmp_path):
    src = _write_source(tmp_path, """\
        def grow(age: int) -> None:
            pass
    """)
    proposals = infer_contracts(src)
    result = apply_contracts(proposals, src)
    assert "import icontract" in result
    assert "@icontract.require(lambda age: age >= 0)" in result


def test_apply_contracts_preserves_existing_import(tmp_path):
    src = _write_source(tmp_path, """\
        import icontract

        def grow(age: int) -> None:
            pass
    """)
    proposals = infer_contracts(src)
    result = apply_contracts(proposals, src)
    assert result.count("import icontract") == 1


def test_apply_contracts_multiple_functions(tmp_path):
    src = _write_source(tmp_path, """\
        def area(width: float, height: float) -> float:
            return width * height

        def divide(a: float, divisor: float) -> float:
            return a / divisor
    """)
    proposals = infer_contracts(src)
    result = apply_contracts(proposals, src)
    assert "@icontract.require(lambda divisor: divisor != 0)" in result
    assert "@icontract.ensure(lambda result: isinstance(result, float))" in result


def test_confidence_increases_with_more_contracts(tmp_path):
    src = _write_source(tmp_path, """\
        def process(count: int, divisor: float) -> int:
            \"\"\"Process items. count must be non-negative.\"\"\"
            if divisor == 0:
                raise ValueError("zero")
            return count
    """)
    proposals = infer_contracts(src)
    assert len(proposals) == 1
    assert proposals[0].confidence > 0.5


def test_proposal_dataclass_fields(tmp_path):
    src = _write_source(tmp_path, """\
        def grow(age: int) -> None:
            pass
    """)
    proposals = infer_contracts(src)
    p = proposals[0]
    assert p.function_name == "grow"
    assert p.file_path == src
    assert p.line_number == 1
    assert isinstance(p.confidence, float)
    assert 0.0 <= p.confidence <= 1.0
    assert isinstance(p.reasoning, str)
    assert len(p.reasoning) > 0
