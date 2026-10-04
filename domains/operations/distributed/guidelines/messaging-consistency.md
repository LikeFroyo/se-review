# Distributed messaging — consistency models, DLQs, and backpressure

Audit asynchronous message handling and event processing.

## What to look for

- **Treating eventual consistency as strong:** Reading from asynchronous message queues or read-replicas immediately after writing and expecting instant visibility.
- **Assuming exactly-once delivery:** Processing message events without deduplication checks on consumer handlers (message delivery is at-least-once). Verify a verifiable mechanism, not intent: a producer-assigned deduplication key (message ID or business idempotency key, never a shared correlation ID), a persistent deduplication record committed atomically with the business side effects (inbox pattern), and side effects designed naturally idempotent (upserts of absolute state) first. Broker-side duplicate filtering is send-side within a bounded window and never sufficient alone.
- **Missing Dead-Letter Queues (DLQ):** Queue consumers without poison-message redirection, causing malformed payloads to loop and stall pipelines.
- **Missing consumer backpressure:** Ingesting messages at unlimited rates without bounding worker queue capacity or acknowledging only after processing.
