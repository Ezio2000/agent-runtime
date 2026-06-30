# Tool Protocol

A tool is an executable capability with a model-neutral `ToolSpec`.

Tools expose:

- `spec.name`
- `spec.description`
- `spec.input_schema`
- `spec.output_schema`
- `spec.annotations`
- `spec.metadata`
- `execute(arguments, context)`

Tool results separate model-visible content from host metadata:

- `parts`: multimodal content parts appended as the tool observation.
- `metadata`: optional small JSON-serializable details.
- `is_error`: whether the result represents a tool failure.

The registry exposes neutral `ToolSpec` values. Provider adapters are
responsible for converting those specs to provider-specific formats such as
OpenAI function tools.

## Scheduling

Tool calls are serial by default. The runtime may execute a consecutive batch of
tool calls concurrently only when all of these are true:

- `LoopLimits.max_parallel_tool_calls` is greater than `1`;
- the tool spec declares `annotations.parallel_safe == true`;
- the tool spec declares `annotations.read_only == true`;
- the tool spec declares `annotations.idempotent == true`.

Unknown tools and tools without those annotations are scheduling barriers and
run serially. Parallel execution affects wall-clock scheduling only: tool
results are still committed to message history in the original model-provided
tool-call order. A serial tool call is checkpointed after its result is
committed. A parallel batch is checkpointed only after the full batch is
committed, so durable snapshots never expose a partial parallel batch.
When `LoopLimits.stop_on_tool_error` is enabled, tool execution is serial even if
`max_parallel_tool_calls` is greater than `1`; this preserves fail-fast behavior
and unambiguous checkpoints.

Common scheduling annotations:

```python
ToolSpec(
    name="search",
    description="Search indexed documents.",
    input_schema={"type": "object"},
    annotations={
        "parallel_safe": True,
        "read_only": True,
        "idempotent": True,
    },
)
```
