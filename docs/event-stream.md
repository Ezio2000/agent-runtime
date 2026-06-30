# Event Stream

The SDK emits neutral runtime events. Applications can adapt these events to
SSE, WebSocket, logs, CLI output, or tests.

Known v0.1 event types:

- `run_started`
- `state_changed`
- `model_started`
- `model_completed`
- `tool_started`
- `tool_completed`
- `checkpoint`
- `final`
- `error`
- `run_completed`

Event `type` is an open string. SDKs should expose these known constants.
`RuntimeHook.on_event` receives an `EventEmitter` and may call
`emitter.emit(type, data)` to append additional events to the same ordered
stream. Other hook methods do not receive an emitter; they should encode data
in returned protocol objects or emit from a later `on_event`.

The core event stream is an orchestration stream, not a provider token stream.
Adapters that need token, reasoning, or progress deltas can add custom event
types without changing the core loop. A `checkpoint` event carries a full
`RunSnapshot` payload after durable state commits and state transitions so host
applications can persist resumable progress.

Events should be JSON-serializable. They should not include the full message
history except for `checkpoint`, whose purpose is durable persistence. Final
output events may include final content parts because they are the run output.

Every event envelope includes:

- `type`: open event type string.
- `data`: event payload.
- `run_id`: stable id shared by all events from a run.
- `sequence`: monotonically increasing run-local sequence.
- `created_at`: wall-clock timestamp.
- `schema_version`: event schema version.
