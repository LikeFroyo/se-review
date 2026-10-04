# Cancellation & task lifecycle — who stops this work, and when

Audit the boundary between spawning work and owning it. The question is never whether the work finishes; it is who cancels it, and what happens to work that is still running when the requester has gone.

## Cancellation not propagated

- **Child spawned without the cancel signal:** A task, thread, or request issued from a handler without receiving the caller's cancellation signal, so a client disconnect or upstream timeout leaves the work running to completion.
- **Cancel signal swallowed by an intermediate layer:** A helper that catches the cancellation, returns normally, and does not re-raise, so everything the caller cancelled also stops being waited for — including the cleanup that cancellation exists to trigger.
- **No cancellation on the downstream call:** The outgoing request carries no timeout and no cancellation, so the caller gives up while the callee keeps working and keeps writing.
- **Cancellation not propagated through the queue:** Work accepted onto a queue has no cancellation path back to the caller, so a cancelled order is still processed and still fulfilled.

## Fire-and-forget tasks

- **No handle retained:** A task started and not awaited, with no reference held, so the runtime may collect it before it runs to completion and the work silently never happens.
- **No error handler attached:** An un-awaited task whose rejection is never observed, so a failure vanishes with no log and no metric.
- **Spawned from a request handler:** A task started as a side effect of handling a request, so it competes with request-serving work for the same executor and adds load exactly when the service is already saturated.
- **Ordering assumed without synchronisation:** A task spawned and immediately followed by code reading the state it was supposed to write, so the read races the write.
