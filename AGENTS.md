# Repository Guidelines

## Project Structure & Module Organization

This repository is a model-neutral agent loop runtime organized for multiple
language SDKs. Cross-language contracts live in `spec/v0`, including schemas
and state-machine notes. Portable behavior cases live in `conformance/cases`.
Design notes are in `docs`. The reference implementation is the Python SDK in
`sdks/python`, with source under `src/agent_runtime` and tests under `tests`.
Runnable examples live in `examples/python`. `sdks/typescript` and `sdks/go`
are reserved for future SDKs.

## Build, Test, and Development Commands

Use `uv` for Python work. Run commands from `sdks/python`:

```bash
uv sync                         # install project and dev dependencies
uv run pytest -q -p no:cacheprovider
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run python ../../examples/python/basic_tool_loop.py
```

If JSON schemas or conformance cases change, parse all JSON files before
handoff.

## Coding Style & Naming Conventions

Python targets 3.11 and uses strict Pyright. Ruff enforces imports, bugbear,
modernization, simplification, and `E/F` rules with a 100-character line limit.
Use 4-space indentation. Keep public runtime types explicit and model-neutral.
Prefer clear module names such as `loop.py`, `scheduler.py`, `messages.py`, and
`tools.py`. Tests should name the behavior being protected.

## Testing Guidelines

Use `pytest` and `pytest-asyncio`. Put Python tests in `sdks/python/tests` using
`test_*.py` files and `test_<behavior>` functions. Add conformance cases for
behavior that all SDKs must share. Core checkpoint, resume, timeout, tool
scheduling, and event-order changes require focused regression tests.

## Commit & Pull Request Guidelines

This repository has no commit history yet. Use concise imperative commits such
as `Add parallel tool scheduling conformance case`. Pull requests should include
a short problem statement, implementation summary, validation commands run, and
links to any related issues. For behavior changes, mention updated spec,
conformance, and docs.

## Agent-Specific Instructions

This project has no historical compatibility burden. Prefer clean breaking
refactors over compatibility shims or legacy aliases. Use sub-agent CRs for
bounded review, and report findings as `Must-Fix`, `Should-Fix`, and
`Looks Good`. Fix credible `Must-Fix` items before handoff.
