# State Machine

The v0.1 state machine has five states:

- `planning`: call the model and ask it for either a final answer or tool calls.
- `executing_tools`: execute requested tool calls and append observations.
- `completed`: terminal state with a final answer.
- `failed`: terminal state for unrecoverable runtime failures.
- `limit_exceeded`: terminal state for iteration, tool-call, or timeout limits.

Transitions:

```text
planning -> completed
planning -> executing_tools
planning -> failed
planning -> limit_exceeded

executing_tools -> planning
executing_tools -> failed
executing_tools -> limit_exceeded
```

Every status change emits `state_changed`, including terminal transitions, and
then emits `checkpoint` with the current `RunSnapshot`. The loop also emits
`checkpoint` after committing a model response to history and after committing
tool observations to history. Serial tools commit one result at a time. Parallel
tool batches commit and checkpoint atomically after every call in the batch has
completed.

Configured timeout limits are enforced as hard async deadlines around model,
tool, and hook awaits. Synchronous hooks run off the event loop so a blocking
hook cannot block the agent loop past the runtime deadline.

During `executing_tools`, the runtime may run explicitly safe tool calls in
parallel up to `LoopLimits.max_parallel_tool_calls`. Unsafe or undeclared tools
remain serial barriers. Tool completion events may arrive in completion order,
but tool observations are committed to message history in the original
tool-call order. If a timeout or other runtime limit interrupts a parallel
batch, the next checkpoint remains at the last fully committed batch boundary.

SDKs should expose `RunSnapshot` as the durable checkpoint boundary. It contains
`AgentState` plus `RuntimeContext`, including wall-clock `started_at` and
`deadline` fields. Host applications own persistence, but they can resume with
`run_snapshot` or `run_snapshot_events`.
