# Process lifecycle — health signalling and shutdown under failure

Audit what the process reports about itself, and what happens to it when the platform asks it to stop.

## Health signalling

- **Liveness coupled to a dependency:** A liveness handler that calls a database, cache, or downstream service, so one dependency's blip makes the platform kill every instance at once.
- **One endpoint for liveness and readiness:** A single `/health` route serving both roles, so readiness never fails without liveness failing too.
- **Health check that cannot fail:** A liveness or readiness handler that always returns 200, or that only proves the process started rather than that it can serve.
- **Recovery-mode health that stays green:** A service that has given up, entered a degraded loop, or lost its configuration connection but still reports healthy, so traffic keeps arriving.

## Graceful shutdown

- **No SIGTERM handling:** The process exits on termination without stopping intake, so the platform kills live requests instead of draining them.
- **Readiness never withdrawn:** New traffic keeps being routed to an instance that is already terminating, because readiness is not flipped before shutdown begins.
- **Consumers killed mid-message:** A queue consumer or batch worker is stopped without finishing and re-acknowledging the message in flight, so completed work is redelivered or half-written work is lost.
- **Grace period shorter than the work:** A termination grace period below the service's own longest request or job, guaranteeing that legitimate work is cut off rather than completed.
