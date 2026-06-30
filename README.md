# agent-runtime

Model-neutral agent loop runtime.

This repository is structured for multiple language SDKs. The Python SDK is the
first implementation and lives in `sdks/python`.

## Project Structure

- `spec/v0`: cross-language runtime contract. Keep state-machine semantics,
  message schemas, event schemas, tool scheduling, limits, and snapshot formats
  here before or alongside SDK changes.
- `conformance/cases`: shared behavior cases every language SDK must satisfy.
  Add cases here for behavior that is part of the core contract, not just a
  Python implementation detail.
- `docs`: design notes for the core runtime, including architecture, event
  stream, state machine, and tool protocol.
- `sdks/python`: first SDK implementation. It is managed with `uv` and is the
  reference implementation until other SDKs catch up.
- `sdks/typescript`: reserved TypeScript SDK location.
- `sdks/go`: reserved Go SDK location.
- `examples/python`: runnable Python examples that should stay small and focused.

## Development Principles

- Core first: keep the agent loop, state machine, event stream, message protocol,
  limits, snapshots, hooks, and tool scheduling model-neutral.
- Open for extension: provider adapters, persistence stores, approval policies,
  tool packs, plugins, and UI integrations should be layered outside the core.
- Break cleanly when needed: this project has no historical compatibility
  burden yet. Prefer a clear breaking refactor over compatibility shims,
  duplicate APIs, or ambiguous transitional behavior.
- No legacy baggage: do not add deprecated aliases, fallback protocols, or
  adapter-specific exceptions unless they are explicitly part of the
  cross-language spec.
- Spec before surface area: if behavior must be portable across SDKs, update
  `spec/v0` and conformance cases instead of documenting it only in Python code.
- Durable state must be resumable: checkpoints must describe states that can be
  resumed without hidden in-memory knowledge. Parallel tool batches therefore
  commit checkpoint state atomically after the full batch completes.
- Small core, strong boundaries: keep scheduling, state mutation, events, hooks,
  model adapters, and tool execution in separate modules with explicit data
  contracts.
- Performance matters: avoid unnecessary blocking in the event loop, preserve
  streaming events, bound parallel tool execution with limits, and keep hot-path
  allocations and deep copies intentional.

## Development Workflow

Use `uv` for Python dependency management and commands. Do not rely on global
Python packages.

```bash
cd sdks/python
uv sync
uv run pytest -q -p no:cacheprovider
uv run ruff check .
uv run ruff format --check .
uv run pyright
```

When changing core behavior:

- Update the Python implementation under `sdks/python/src/agent_runtime`.
- Add focused Python regression tests under `sdks/python/tests`.
- Add or update conformance cases under `conformance/cases` for portable
  behavior.
- Update `spec/v0` when the behavior is part of the SDK contract.
- Update `docs` when the design model, state machine, event stream, or tool
  protocol changes.
- Keep examples minimal and runnable.

Before handoff, run at least:

```bash
cd sdks/python
uv run pytest -q -p no:cacheprovider
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run python ../../examples/python/basic_tool_loop.py
```

If JSON spec or conformance files changed, also verify they parse:

```bash
cd sdks/python
uv run python - <<'PY'
import json
from pathlib import Path

for root in ["../../spec/v0", "../../conformance/cases"]:
    for path in sorted(Path(root).glob("*.json")):
        json.loads(path.read_text())
print("json ok")
PY
```

## Sub-Agent CR Guidelines

Use sub-agents for bounded code review or verification tasks when parallel
review materially improves confidence. Keep their scope narrow and concrete.

Sub-agent CR prompts should include:

- The exact behavior or risk to review.
- The files or modules that define the behavior.
- Whether the agent is read-only or owns a disjoint write scope.
- The validation commands it should run.
- The required report format: `Must-Fix`, `Should-Fix`, and `Looks Good`.

Review severity:

- `Must-Fix`: correctness bugs, broken resumability, contract/spec mismatch,
  failing tests, data loss risk, or behavior that invalidates the core runtime
  model.
- `Should-Fix`: maintainability, naming, missing narrow tests, unclear docs, or
  non-blocking design inconsistencies.
- `Looks Good`: confirmed invariants, tests run, and any residual risk.

Sub-agent CR rules:

- Do not treat sub-agent output as a substitute for local validation.
- Fix every credible `Must-Fix` before handoff or explicitly document why it is
  rejected.
- After fixing a `Must-Fix`, rerun local validation and request a narrow
  re-review when the risk is subtle.
- Close completed sub-agents after consuming their report.
- The final handoff should mention sub-agent findings only when they affected
  the implementation or materially increase confidence.
