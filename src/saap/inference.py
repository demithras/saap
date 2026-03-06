"""Contract inference engine for proposing icontract decorators."""

from __future__ import annotations

import ast
import difflib
import re
import textwrap
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ContractProposal:
    function_name: str
    file_path: Path
    line_number: int
    preconditions: list[str] = field(default_factory=list)
    postconditions: list[str] = field(default_factory=list)
    confidence: float = 0.0
    reasoning: str = ""


_NON_NEGATIVE_NAMES = frozenset({
    "age", "count", "size", "length", "width", "height", "depth",
    "weight", "quantity", "amount", "index", "capacity", "limit",
    "max_size", "min_size", "num", "number", "total", "duration",
})

_SKIP_PATH_NAMES = frozenset({
    "path", "file", "filename", "filepath", "file_path", "dir", "directory",
})

_DIVISION_NAMES = frozenset({"divisor", "denominator"})

_DOCSTRING_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(\w+)\s+must be\s+positive", re.IGNORECASE),
     "lambda {name}: {name} > 0"),
    (re.compile(r"(\w+)\s+must be\s+non-negative", re.IGNORECASE),
     "lambda {name}: {name} >= 0"),
    (re.compile(r"(\w+)\s+must be\s+non-empty", re.IGNORECASE),
     "lambda {name}: len({name}) > 0"),
    (re.compile(r"(\w+)\s+must not be\s+None", re.IGNORECASE),
     "lambda {name}: {name} is not None"),
    (re.compile(r"(\w+)\s+should be\s+positive", re.IGNORECASE),
     "lambda {name}: {name} > 0"),
    (re.compile(r"(\w+)\s+should be\s+non-negative", re.IGNORECASE),
     "lambda {name}: {name} >= 0"),
    (re.compile(r"(\w+)\s+should be\s+non-empty", re.IGNORECASE),
     "lambda {name}: len({name}) > 0"),
    (re.compile(r"(\w+)\s+should not be\s+None", re.IGNORECASE),
     "lambda {name}: {name} is not None"),
]


def _is_optional_type(annotation: ast.expr) -> bool:
    if isinstance(annotation, ast.Subscript):
        if isinstance(annotation.value, ast.Name) and annotation.value.id == "Optional":
            return True
    if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        for operand in (annotation.left, annotation.right):
            if isinstance(operand, ast.Constant) and operand.value is None:
                return True
    return False


def _annotation_to_type_name(annotation: ast.expr) -> str | None:
    if isinstance(annotation, ast.Name):
        return annotation.id
    if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
        return annotation.value
    return None


def _find_division_params(func: ast.FunctionDef) -> set[str]:
    params = set()
    for node in ast.walk(func):
        if isinstance(node, (ast.Div, ast.FloorDiv)):
            pass
    for node in ast.walk(func):
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Div, ast.FloorDiv)):
            if isinstance(node.right, ast.Name):
                params.add(node.right.id)
    return params


def _infer_from_guard_clauses(func: ast.FunctionDef) -> list[str]:
    preconditions: list[str] = []
    for stmt in func.body:
        if isinstance(stmt, ast.If):
            # Pattern: if x < 0: raise ValueError
            if (
                len(stmt.body) == 1
                and isinstance(stmt.body[0], ast.Raise)
            ):
                test = stmt.test
                pre = _negate_condition(test)
                if pre:
                    preconditions.append(pre)
    return preconditions


def _negate_condition(test: ast.expr) -> str | None:
    if isinstance(test, ast.Compare) and len(test.ops) == 1 and len(test.comparators) == 1:
        left = test.left
        op = test.ops[0]
        right = test.comparators[0]
        left_src = _expr_to_source(left)
        right_src = _expr_to_source(right)
        if left_src is None or right_src is None:
            return None
        negated_op = _negate_cmp_op(op)
        if negated_op is None:
            return None
        return f"lambda {left_src}: {left_src} {negated_op} {right_src}"
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        inner = _expr_to_source(test.operand)
        if inner is not None:
            return f"lambda {inner}: {inner}"
    return None


def _negate_cmp_op(op: ast.cmpop) -> str | None:
    mapping: dict[type, str] = {
        ast.Lt: ">=",
        ast.LtE: ">",
        ast.Gt: "<=",
        ast.GtE: "<",
        ast.Eq: "!=",
        ast.NotEq: "==",
        ast.Is: "is not",
        ast.IsNot: "is",
    }
    return mapping.get(type(op))


def _expr_to_source(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Constant):
        return repr(node.value)
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return f"{node.value.id}.{node.attr}"
    return None


def _infer_from_docstring(docstring: str) -> list[str]:
    preconditions: list[str] = []
    for pattern, template in _DOCSTRING_PATTERNS:
        for match in pattern.finditer(docstring):
            name = match.group(1)
            preconditions.append(template.format(name=name))
    return preconditions


def _analyze_function(
    func: ast.FunctionDef,
    file_path: Path,
) -> ContractProposal | None:
    preconditions: list[str] = []
    postconditions: list[str] = []
    reasons: list[str] = []

    param_names = {arg.arg for arg in func.args.args if arg.arg != "self"}
    division_params = _find_division_params(func) & param_names

    for arg in func.args.args:
        name = arg.arg
        if name == "self":
            continue

        if name in _SKIP_PATH_NAMES:
            continue

        annotation = arg.annotation
        is_optional = annotation is not None and _is_optional_type(annotation)

        if is_optional:
            continue

        if name in _DIVISION_NAMES or name in division_params:
            preconditions.append(f"lambda {name}: {name} != 0")
            reasons.append(f"'{name}' used as divisor")

        if annotation is not None:
            type_name = _annotation_to_type_name(annotation)
            if type_name in ("int", "float") and name in _NON_NEGATIVE_NAMES:
                pre = f"lambda {name}: {name} >= 0"
                if pre not in preconditions:
                    preconditions.append(pre)
                    reasons.append(f"'{name}' is a non-negative quantity by convention")

    # Return type postcondition
    if func.returns is not None and not _is_optional_type(func.returns):
        type_name = _annotation_to_type_name(func.returns)
        if type_name is not None:
            postconditions.append(f"lambda result: isinstance(result, {type_name})")
            reasons.append(f"return type annotated as {type_name}")

    # Guard clause analysis
    guard_pres = _infer_from_guard_clauses(func)
    for pre in guard_pres:
        if pre not in preconditions:
            preconditions.append(pre)
            reasons.append("guard clause detected")

    # Docstring analysis
    docstring = ast.get_docstring(func)
    if docstring:
        doc_pres = _infer_from_docstring(docstring)
        for pre in doc_pres:
            if pre not in preconditions:
                preconditions.append(pre)
                reasons.append("docstring constraint")

    if not preconditions and not postconditions:
        return None

    total = len(preconditions) + len(postconditions)
    confidence = min(1.0, 0.3 + 0.15 * total)

    return ContractProposal(
        function_name=func.name,
        file_path=file_path,
        line_number=func.lineno,
        preconditions=preconditions,
        postconditions=postconditions,
        confidence=round(confidence, 2),
        reasoning="; ".join(reasons),
    )


def infer_contracts(source_path: Path) -> list[ContractProposal]:
    source = source_path.read_text()
    tree = ast.parse(source, filename=str(source_path))
    proposals: list[ContractProposal] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            proposal = _analyze_function(node, source_path)
            if proposal is not None:
                proposals.append(proposal)
    return proposals


def apply_contracts(
    proposals: list[ContractProposal],
    source_path: Path,
) -> str:
    source = source_path.read_text()
    lines = source.splitlines(keepends=True)

    # Ensure trailing newline for consistent handling
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"

    # Sort proposals by line number descending so insertions don't shift later lines
    sorted_proposals = sorted(proposals, key=lambda p: p.line_number, reverse=True)

    for proposal in sorted_proposals:
        idx = proposal.line_number - 1
        func_line = lines[idx]
        indent = " " * (len(func_line) - len(func_line.lstrip()))

        decorator_lines: list[str] = []
        for pre in proposal.preconditions:
            decorator_lines.append(f"{indent}@icontract.require({pre})\n")
        for post in proposal.postconditions:
            decorator_lines.append(f"{indent}@icontract.ensure({post})\n")

        # Find the first decorator or the def line itself
        insert_idx = idx
        while insert_idx > 0 and lines[insert_idx - 1].strip().startswith("@"):
            insert_idx -= 1

        lines[insert_idx:insert_idx] = decorator_lines

    result = "".join(lines)

    # Add import if needed
    if "import icontract" not in result:
        # Insert after any existing imports or at top
        result_lines = result.splitlines(keepends=True)
        insert_pos = 0
        for i, line in enumerate(result_lines):
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                insert_pos = i + 1
            elif stripped and not stripped.startswith("#") and not stripped.startswith('"""') and insert_pos > 0:
                break
        result_lines.insert(insert_pos, "import icontract\n")
        result = "".join(result_lines)

    return result


def format_diff(
    proposals: list[ContractProposal],
    source_path: Path,
) -> str:
    original = source_path.read_text().splitlines(keepends=True)
    modified = apply_contracts(proposals, source_path).splitlines(keepends=True)
    diff = difflib.unified_diff(
        original,
        modified,
        fromfile=str(source_path),
        tofile=str(source_path),
    )
    return "".join(diff)
