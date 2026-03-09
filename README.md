# SAAP

**Scientific Approach Automation Pipeline** — automated contract-based verification for Python.

SAAP turns the "golden chain" of software correctness into a single command:
**contracts &rarr; property-based testing &rarr; symbolic execution &rarr; mutation testing**.

## How It Works

SAAP analyzes your Python code and runs a tiered verification pipeline:

| Tier | Runners | When |
|------|---------|------|
| 1 | icontract | Basic contract validation |
| 2 | icontract, Hypothesis | Contracts detected &mdash; add property-based testing |
| 3 | icontract, Hypothesis, CrossHair, mutmut | Critical code &mdash; full verification |

Tier is auto-detected from source analysis (C-extensions, existing contracts, criticality config), or forced by context (`pre-commit` caps at 1, `audit` forces 3).

## Install

```bash
pip install -e .            # Core
pip install -e ".[dev]"     # Dev + mutation testing
```

Requires Python 3.11+.

## Usage

### Contract Inference

Analyze code and propose `@require` / `@ensure` decorators:

```python
from pathlib import Path
from saap.inference import infer_contracts, format_diff

proposals = infer_contracts(Path("mymodule.py"))
for p in proposals:
    print(f"{p.function_name} (line {p.line_number}, confidence {p.confidence:.2f}):")
    for pre in p.preconditions:
        print(f"  @require({pre})")
    for post in p.postconditions:
        print(f"  @ensure({post})")

# Unified diff showing where decorators would be inserted
print(format_diff(proposals, Path("mymodule.py")))
```

The inference engine detects patterns like:
- Guard clauses (`if x < 0: raise` &rarr; `@require(lambda x: x >= 0)`)
- Docstring phrases ("must be positive" &rarr; `@require(lambda x: x > 0)`)
- Division operands (`divisor` &rarr; `@require(lambda divisor: divisor != 0)`)
- Non-negative quantity names (`count`, `size`, `amount` &rarr; `>= 0`)

### Verification Pipeline

Detect tier, dispatch runners, collect results:

```python
from pathlib import Path
from saap.dispatcher import detect_tier, dispatch
from saap.runners import get_runners
from saap.reporter import report_console, ReportContext
from saap.config import load_config

target = Path("mymodule.py")
config = load_config()

tier = detect_tier(target, context="manual", config=config)
runner_names = dispatch(target, context="manual", config=config)
runners = get_runners(runner_names)

results = []
for runner in runners:
    if runner.is_available():
        results.append(runner.run(target))

ctx = ReportContext(target=target, tier=tier, context="manual")
print(report_console(results, ctx))
```

Example output:

```
============================================================
SAAP Verification Report
------------------------------------------------------------
Target  : mymodule.py
Tier    : 2
Context : manual
============================================================
  [PASS] icontract            0.01s
         All contracts satisfied
  [PASS] hypothesis           0.34s
         PBT: 3/3 passed
------------------------------------------------------------
Overall : PASS  |  Total duration: 0.35s
============================================================
```

### Configuration

Create `saap.toml` in your project root:

```toml
[saap]
default_tier = 2
excluded_paths = ["migrations/", "vendor/"]

[saap.critical]
functions = ["process_payment", "calculate_tax"]
modules = ["auth/", "billing/"]

[saap.runners]
icontract = true
hypothesis = true
crosshair = true
mutmut = false

[saap.report]
format = "console"   # or "quarto", "logseq"
```

### Dogfooding

SAAP runs its inference engine against its own source code in CI:

```bash
python scripts/dogfood.py
```

## Architecture

```
src/saap/
  config.py        # Config loader (saap.toml discovery)
  dispatcher.py    # Tier detection + runner dispatch
  inference.py     # Contract proposal engine (AST analysis)
  reporter.py      # Output formatters (console, Quarto, Logseq)
  runners/
    _base.py               # Runner protocol + RunResult
    icontract_runner.py    # In-process contract execution
    hypothesis_runner.py   # Property-based testing via icontract-hypothesis
    crosshair_runner.py    # Symbolic execution (subprocess)
    mutmut_runner.py       # Mutation testing (subprocess)
  templates/
    default.qmd    # Quarto report template
```

## Dependencies

| Package | Role |
|---------|------|
| [icontract](https://github.com/Parquery/icontract) | Runtime contract enforcement |
| [icontract-hypothesis](https://github.com/mristin/icontract-hypothesis) | Contract-to-Hypothesis bridge |
| [Hypothesis](https://hypothesis.readthedocs.io/) | Property-based testing |
| [CrossHair](https://github.com/pschanely/CrossHair) | Symbolic execution / contract proving |
| [mutmut](https://github.com/boxed/mutmut) | Mutation testing (optional) |

## License

MIT
