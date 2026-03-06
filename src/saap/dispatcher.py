"""Smart dispatcher: analyze source files to determine verification tier."""

from __future__ import annotations

import ast
from pathlib import Path

from saap.config import SaapConfig

# Tier → runner sets
TIER_RUNNERS: dict[int, list[str]] = {
    1: ["icontract"],
    2: ["icontract", "hypothesis"],
    3: ["icontract", "hypothesis", "crosshair", "mutmut"],
}

# Imports that signal C-extension usage
C_EXTENSION_MODULES = frozenset({"ctypes", "cffi", "_ctypes"})

# icontract decorator names
ICONTRACT_DECORATORS = frozenset({"require", "ensure"})

# Context → tier ceiling/floor
CONTEXT_RULES: dict[str, tuple[int | None, int | None]] = {
    # (min_tier, max_tier)
    "manual": (None, None),
    "pre-commit": (None, 1),
    "pr": (None, 2),
    "audit": (3, None),
}


def _has_icontract_decorators(tree: ast.Module) -> bool:
    """Check whether any function/method uses @require or @ensure."""
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            name: str | None = None
            if isinstance(dec, ast.Name):
                name = dec.id
            elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name):
                name = dec.func.id
            elif isinstance(dec, ast.Attribute):
                name = dec.attr
            elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                name = dec.func.attr
            if name in ICONTRACT_DECORATORS:
                return True
    return False


def _imports_c_extensions(tree: ast.Module) -> bool:
    """Check whether the file imports any C-extension modules."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in C_EXTENSION_MODULES:
                    return True
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                if top in C_EXTENSION_MODULES:
                    return True
    return False


def _has_critical_functions(tree: ast.Module, critical_functions: list[str]) -> bool:
    """Check whether any function name matches the critical list."""
    if not critical_functions:
        return False
    crit = set(critical_functions)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in crit:
                return True
    return False


def _is_critical_module(source_path: Path, critical_modules: list[str]) -> bool:
    """Check whether the source file path matches any critical module pattern."""
    if not critical_modules:
        return False
    path_str = str(source_path)
    return any(pattern in path_str for pattern in critical_modules)


def detect_tier(
    source_path: Path,
    context: str = "manual",
    config: SaapConfig | None = None,
) -> int:
    """Determine verification tier for a source file.

    Args:
        source_path: Path to the Python source file.
        context: Execution context — "manual", "pre-commit", "pr", or "audit".
        config: Optional SAAP configuration. Defaults are used when None.

    Returns:
        Tier number (1, 2, or 3).
    """
    if config is None:
        config = SaapConfig()

    min_tier, max_tier = CONTEXT_RULES.get(context, (None, None))

    # Audit always forces tier 3
    if min_tier is not None:
        return min_tier

    # Parse source AST
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(source_path))

    # Start from config default
    tier = config.default_tier

    # No contracts → tier 1 only
    if not _has_icontract_decorators(tree):
        tier = 1
    else:
        # C extensions or critical code → tier 3
        if _imports_c_extensions(tree):
            tier = 3
        if _has_critical_functions(tree, config.critical.functions):
            tier = 3
        if _is_critical_module(source_path, config.critical.modules):
            tier = 3

    # Apply context ceiling
    if max_tier is not None:
        tier = min(tier, max_tier)

    return tier


def dispatch(
    source_path: Path,
    context: str = "manual",
    config: SaapConfig | None = None,
) -> list[str]:
    """Return the list of runner names to execute for a source file.

    Args:
        source_path: Path to the Python source file.
        context: Execution context — "manual", "pre-commit", "pr", or "audit".
        config: Optional SAAP configuration. Defaults are used when None.

    Returns:
        List of runner names, e.g. ["icontract", "hypothesis"].
    """
    if config is None:
        config = SaapConfig()

    tier = detect_tier(source_path, context, config)
    runners_cfg = config.runners
    all_runners = TIER_RUNNERS[tier]

    # Filter by config-enabled runners
    enabled = {
        "icontract": runners_cfg.icontract,
        "hypothesis": runners_cfg.hypothesis,
        "crosshair": runners_cfg.crosshair,
        "mutmut": runners_cfg.mutmut,
    }

    return [r for r in all_runners if enabled.get(r, False)]
