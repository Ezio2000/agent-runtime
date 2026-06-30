# Architecture

`agent-runtime` is a small execution kernel for tool-using agents.

The core SDK owns:

- a lightweight state machine;
- model/tool protocol interfaces;
- loop limits;
- event stream emission;
- runtime context, hook slots, and serializable run snapshots.

Host applications own:

- HTTP, SSE, WebSocket, or CLI adapters;
- persistence;
- user authentication;
- concrete model clients;
- concrete tools.

The v0.1 runtime intentionally excludes concrete checkpoint stores, approval
UIs, memory implementations, sandboxing, MCP, and subagents. Those are
extension concerns. The core exposes neutral hooks, context, and state
serialization so host applications can add those behaviors without changing the
loop. Durable progress is represented as `RunSnapshot`; storage and retention
policy stay outside the core SDK.
