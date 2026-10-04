"""Approval workflow — a request waits until a reviewer acts.

Policy: a PENDING request expires after APPROVAL_TTL_SECONDS and must be
re-submitted rather than approved late.
"""
import time
from dataclasses import dataclass
from enum import Enum

APPROVAL_TTL_SECONDS = 3600


class State(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class Request:
    state: State = State.PENDING
    created_at: float = 0.0


def approve(request: Request) -> None:
    if request.state is not State.PENDING:
        raise ValueError("cannot approve a decided request")
    request.state = State.APPROVED


def reject(request: Request) -> None:
    if request.state is not State.PENDING:
        raise ValueError("cannot reject a decided request")
    request.state = State.REJECTED
