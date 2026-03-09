"""Package-aware module loader for SAAP runners.

Handles relative imports by detecting when a target file lives inside a
Python package (has __init__.py siblings) and setting up the package
hierarchy in sys.modules before exec_module().
"""
from __future__ import annotations

import importlib
import importlib.util
import sys
import types
from pathlib import Path


def load_module_from_path(target: Path) -> types.ModuleType:
    """Load a Python module from a file path, handling package context.

    If the target is inside a package (directory with __init__.py),
    the package is registered in sys.modules so relative imports work.

    Raises ImportError if the module cannot be loaded.
    """
    resolved = target.resolve()

    # Detect package hierarchy by walking up to find __init__.py files
    package_parts: list[str] = []
    current = resolved.parent
    while (current / "__init__.py").exists():
        package_parts.insert(0, current.name)
        current = current.parent

    if package_parts:
        # Target is inside a package — set up the hierarchy
        package_root = current  # Directory above the top-level package
        if str(package_root) not in sys.path:
            sys.path.insert(0, str(package_root))

        # Register each level of the package in sys.modules
        for i in range(len(package_parts)):
            pkg_name = ".".join(package_parts[: i + 1])
            if pkg_name not in sys.modules:
                pkg_dir = package_root / Path(*package_parts[: i + 1])
                init_path = pkg_dir / "__init__.py"
                pkg_spec = importlib.util.spec_from_file_location(
                    pkg_name,
                    str(init_path),
                    submodule_search_locations=[str(pkg_dir)],
                )
                if pkg_spec and pkg_spec.loader:
                    pkg_mod = importlib.util.module_from_spec(pkg_spec)
                    sys.modules[pkg_name] = pkg_mod
                    pkg_spec.loader.exec_module(pkg_mod)

        # Now load the target module with its fully qualified name
        module_name = ".".join(package_parts + [resolved.stem])
        spec = importlib.util.spec_from_file_location(module_name, str(resolved))
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not create module spec for {target}")

        module = importlib.util.module_from_spec(spec)
        module.__package__ = ".".join(package_parts)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    else:
        # Standalone module — original behavior
        module_name = resolved.stem
        spec = importlib.util.spec_from_file_location(module_name, str(resolved))
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not create module spec for {target}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
