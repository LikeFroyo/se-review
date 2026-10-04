# Tool use & agency — what the model is allowed to do

Audit the boundary between a model's *proposal* and the system's *action*. Every capability reachable from a model is reachable by whoever can influence its context.

## What to look for

- **No tool allowlist:** Every function, client, or endpoint the process can reach is offered to the model, including administrative and infrastructure calls, so a single injected instruction can do anything the process can.
- **Capability exceeds the requester's:** A tool invoked with the service's own credentials or scope for a user who would be denied directly, so the model launders privilege through the agent.
- **Destructive action without confirmation:** A delete, a payment, a permission change, or an outbound message taken from a single model turn with no human confirmation step and no dry-run.
- **Unbounded agent loop:** A tool-calling loop with no maximum iteration count, no token or cost ceiling, and no stopping condition, so a model that keeps calling runs until it exhausts a budget.
- **Tool result trusted as a completion:** A tool's return value, error message, or fetched page appended to the conversation and treated as authoritative instruction content.
- **Credential exposed to the model:** An API key, connection string, or session token placed in the prompt or in the tool schema, so it is included in completions, logs, and traces.
- **Side effect without an audit record:** An action the model caused recorded only as a log line, with no record of which model, prompt, and tool call produced it.
- **Tool errors retried blindly:** A failing tool call retried on the same arguments, so a transient failure becomes repeated side effects.
