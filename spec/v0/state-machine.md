# Agent Runtime v0 State Machine

Status values:

- `planning`
- `executing_tools`
- `completed`
- `failed`
- `limit_exceeded`

The loop starts in `planning`.

When the model returns tool calls, the runtime appends the assistant tool-call
message and transitions to `executing_tools`.

When all tool observations are appended, the runtime returns to `planning`.

When the model returns no tool calls, the runtime completes with the model
content parts as the final answer.

The runtime must stop with `limit_exceeded` when any configured limit is
exceeded.

SDKs must emit `state_changed` for every status transition, including terminal
transitions to `completed`, `failed`, and `limit_exceeded`.

SDKs must expose a durable `RunSnapshot` value containing `AgentState` and
`RuntimeContext`. A `checkpoint` event must be emitted after each model response
is committed to message history, after tool observations are committed to
message history and removed from `pending_tool_calls`, and after each state
transition. Serial tool calls commit one result at a time; parallel tool batches
commit atomically as specified in `tool-scheduling.md`.
`RuntimeContext.started_at` and `RuntimeContext.deadline` are wall-clock epoch
seconds; SDKs may use monotonic clocks internally for live timeout enforcement.

For terminal failures and limits, SDKs should emit `state_changed`, then
`checkpoint`, then `error`, then `run_completed`.

Tool scheduling semantics, including simple parallel execution, are specified in
`tool-scheduling.md`.
