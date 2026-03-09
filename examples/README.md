# SAAP Examples

Demonstrates the full SAAP golden chain: **Inference → Diff → Dispatch → Report**.

## Quick Start

```bash
# From the repo root
python examples/demo.py
```

## What's Inside

| File | Description |
|------|-------------|
| `modules/billing.py` | Un-contracted billing functions (5 functions, all 5 inference heuristics) |
| `modules/inventory.py` | Un-contracted inventory functions (3 functions, complementary patterns) |
| `modules/billing_contracted.py` | Same billing functions with `@icontract.require`/`@icontract.ensure` applied |
| `demo.py` | Orchestrator that runs all 4 stages end-to-end |

## The 4 Stages

1. **INFERENCE** — `infer_contracts()` analyzes billing.py and inventory.py, proposing preconditions and postconditions from code patterns
2. **DIFF** — `format_diff()` shows unified diffs of what the decorators would look like
3. **DISPATCH** — `detect_tier()` + `dispatch()` determines which runners to use based on contract presence and execution context
4. **REPORT** — `report_console()` + `report_logseq()` format synthetic run results for different output channels
