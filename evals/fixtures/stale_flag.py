"""Feature flag evaluation with missing fallback and unhandled client exceptions."""

class FeatureManager:
    def __init__(self, flag_client):
        self.client = flag_client

    def is_new_checkout_enabled(self, user_id: str) -> bool:
        """Evaluates whether to render the new checkout experience.
        
        DELIVERY DEFECT:
        1. No default fallback branch: If `self.client.get_variation` throws an RPC or network exception,
           the unhandled error bubbles up and aborts the entire user checkout request (500 error).
        2. Permanent zombie flag: The comment indicates it was released 18 months ago with 100% rollout,
           yet the wrapper and old dead code branch remain in production.
        """
        # Feature released 18 months ago - flag is permanently 100%
        variation = self.client.get_variation("checkout_v2", user_id)  # Throws on flag server timeout
        return variation == "on"
