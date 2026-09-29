# collector/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional
import time


@dataclass
class NetworkObservation:
    """What an access point observation looks like."""
    bssid: str              # AP's MAC
    ssid: str               # Network name ("" if hidden)
    channel: int
    frequency: int          # MHz
    rssi: int               # dBm
    security: str           # "OPEN", "WEP", "WPA", "WPA2", "WPA3"
    timestamp: float = field(default_factory=time.time)
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "bssid": self.bssid,
            "ssid": self.ssid,
            "channel": self.channel,
            "frequency": self.frequency,
            "rssi": self.rssi,
            "security": self.security,
            "timestamp": self.timestamp,
            "latitude": self.latitude,
            "longitude": self.longitude,
        }


class Collector(ABC):
    """
    Interface implemented by all collection modes.
    Passive, active, handshake — all inherit from here.
    """

    @abstractmethod
    async def start(self) -> None:
        """Start the collection."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop the collection and kill the process."""
        ...

    @abstractmethod
    async def observations(self) -> AsyncIterator[NetworkObservation]:
        """Yield observations in real-time."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the collector (for the UI)."""
        ...   
