"""Concurrent transfer service with lock-order inversion deadlock."""
import threading
import time

class Account:
    def __init__(self, account_id: str, balance: float):
        self.account_id = account_id
        self.balance = balance
        self.lock = threading.Lock()

def transfer(source: Account, target: Account, amount: float) -> bool:
    """Transfer funds between accounts.
    
    BUG: Acquires locks in argument order instead of a globally ordered sequence (e.g. sorted by account_id).
    When Thread 1 transfers A -> B and Thread 2 transfers B -> A concurrently,
    Thread 1 holds A.lock and waits for B.lock, while Thread 2 holds B.lock and waits for A.lock -> DEADLOCK.
    """
    with source.lock:
        time.sleep(0.01)  # Simulates I/O or processing window
        with target.lock:
            if source.balance >= amount:
                source.balance -= amount
                target.balance += amount
                return True
            return False
