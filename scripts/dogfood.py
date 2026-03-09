#!/usr/bin/env python3
"""Run SAAP's inference engine against its own source code (dogfooding).

This script exercises the golden chain on SAAP itself, verifying that
the inference engine can analyze real-world Python without errors and
reporting any contract proposals it discovers.
"""

from __future__ import annotations

import sys
from pathlib import Path

from saap.inference import infer_contracts


def main() -> int:
    src_dir = Path("src/saap")
    if not src_dir.exists():
        print(f"ERROR: {src_dir} not found. Run from the repo root.", file=sys.stderr)
        return 1

    files = sorted(src_dir.rglob("*.py"))
    total_proposals = 0
    total_files = 0
    files_with_proposals = 0

    print(f"Running SAAP inference on {len(files)} source files...\n")

    for f in files:
        total_files += 1
        proposals = infer_contracts(f)
        if proposals:
            files_with_proposals += 1
            total_proposals += len(proposals)
            print(f"  {f}: {len(proposals)} contract proposals")
            for p in proposals:
                pre = len(p.preconditions)
                post = len(p.postconditions)
                print(f"    - {p.function_name} (line {p.line_number}): "
                      f"{pre} pre, {post} post, confidence={p.confidence:.2f}")

    print(f"\nSummary: {total_proposals} proposals across "
          f"{files_with_proposals}/{total_files} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
