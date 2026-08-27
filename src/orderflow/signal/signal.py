from dataclasses import dataclass
from enum import Enum


class SignalSide(Enum):

    LONG = "LONG"

    SHORT = "SHORT"

    FLAT = "FLAT"


@dataclass
class Signal:

    timestamp: int

    side: SignalSide

    strength: float

    reason: str
