# Retries & backoff — exponential delays, jitter, and retry budgets

Audit retry logic against thundering-herd risks and amplification attacks.

## What to look for

- **Immediate retries:** Retrying failed requests in a tight loop (`for _ in range(5): do_request()`) with no delay, keeping overloaded downstreams saturated.
- **Missing jitter:** Exponential backoff with static intervals causing synchronized client herds to strike the backend simultaneously.
- **Layered retry amplification:** Retrying at multiple architectural layers (e.g. 3 attempts in client, 3 in gateway, 3 in service = 27 attempts).
- **Missing retry budgets:** Retrying indefinitely or without a circuit budget, preventing service recovery during widespread dependency outages.
- **Retrying non-idempotent operations:** Automatically retrying mutating state requests without idempotency keys.
