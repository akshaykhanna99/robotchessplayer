"""Structured events emitted by the control centre controller."""

from __future__ import annotations

from dataclasses import dataclass
import time


@dataclass(frozen=True)
class ControlCentreEvent:
    category: str
    message: str
    timestamp: float


def make_event(category: str, message: str) -> ControlCentreEvent:
    return ControlCentreEvent(category=category, message=message, timestamp=time.time())
