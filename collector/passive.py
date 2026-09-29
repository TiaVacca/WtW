# collector/passive.py
import asyncio
import re
from typing import AsyncIterator, Optional

from scapy.all import (
    Dot11, Dot11Beacon, Dot11Elt, RadioTap,
    sniff,
)
from scapy.layers.dot11 import Dot11

from .base import Collector, NetworkObservation

# Channel Mapping → frequency (2.4 GHz)
CHANNEL_FREQ_2G = {ch: 2407 + ch * 5 for ch in range(1, 14)}
# 5 GHz (subset, the principals ones)
CHANNEL_FREQ_5G = {
    36: 5180, 40: 5200, 44: 5220, 48: 5240,
    52: 5260, 56: 5280, 60: 5300, 64: 5320,
    100: 5500, 104: 5520, 108: 5540, 112: 5560,
    116: 5580, 120: 5600, 124: 5620, 128: 5640,
    132: 5660, 136: 5680, 140: 5700, 144: 5720,
    149: 5745, 153: 5765, 157: 5785, 161: 5805, 165: 5825,
}


def channel_to_freq(channel: int) -> int:
    if channel in CHANNEL_FREQ_5G:
        return CHANNEL_FREQ_5G[channel]
    return CHANNEL_FREQ_2G.get(channel, 0)


def detect_security(packet) -> str:
    """extract security type from capability + RSN/WPA IE."""
    if not packet.haslayer(Dot11Beacon):
        return "UNKNOWN"

    cap = packet[Dot11Beacon].cap
    # Bit 1 = Privacy (WEP), but need the rest to distinguish WPA/WPA2/WPA3
    is_wep = bool(cap & 0x0040)  # privacy bit

    # search for RSN (WPA2/WPA3) and WPA (WPA1)
    for i in range(len(packet)):
        try:
            elt = packet[i]
            if isinstance(elt, Dot11Elt):
                eid = elt.ID
                if eid == 48:  # RSN Information Element
                    return "WPA2"
                if eid == 221:  # WPA (vendor specific)
                    return "WPA"
        except (IndexError, Exception):
            continue

    if is_wep:
        return "WEP"
    return "OPEN"


class PassiveCollector(Collector):
    """
    Passive scanner: listens for beacon frames in monitor mode.
    Implements channel hopping (1s per channel).
    """

    def __init__(self, iface: str = "wlan0mon",
                 gps_func=None,
                 channels: list[int] | None = None):
        self.iface = iface
        self.gps_func = gps_func  # callable → (lat, lon) | None
        self.channels = channels or [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 36, 40, 44, 48, 149, 153, 157, 161, 165]
        self._queue: asyncio.Queue[NetworkObservation] = asyncio.Queue()
        self._running = False
        self._task: Optional[asyncio.Task] = None

    @property
    def name(self) -> str:
        return "passive-scanner"

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._channel_hopper())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def observations(self) -> AsyncIterator[NetworkObservation]:
        while self._running or not self._queue.empty():
            try:
                obs = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                yield obs
            except asyncio.TimeoutError:
                continue

    async def _channel_hopper(self) -> None:
        """Change channel every second, sniffing beacons."""
        import subprocess
        while self._running:
            for ch in self.channels:
                if not self._running:
                    break
                try:
                    subprocess.run(
                        ["iw", self.iface, "set", "channel", str(ch)],
                        check=True, capture_output=True
                    )
                except (subprocess.CalledProcessError, FileNotFoundError):
                    pass  # in dev whitout real hw

                # Sniff for a 1 second on this channel
                packets = await asyncio.get_event_loop().run_in_executor(
                    None, self._sniff_channel, ch
                )
                for pkt in packets:
                    await self._queue.put(pkt)

    def _sniff_channel(self, channel: int) -> list[NetworkObservation]:
        """Sniff synchronously (in executor) for 1s."""
        results = []

        def handler(pkt):
            if pkt.haslayer(Dot11Beacon):
                obs = self._parse_beacon(pkt, channel)
                if obs:
                    results.append(obs)

        sniff(
            iface=self.iface,
            prn=handler,
            store=0,
            timeout=1.0,
            filter="type mgt subtype beacon",
        )
        return results

    def _parse_beacon(self, pkt, channel: int) -> Optional[NetworkObservation]:
        bssid = pkt[Dot11].addr2
        ssid = ""
        if pkt.haslayer(Dot11Elt):
            for i in range(len(pkt)):
                try:
                    elt = pkt[i]
                    if isinstance(elt, Dot11Elt) and elt.ID == 0:
                        ssid = elt.info.decode("utf-8", errors="ignore")
                        break
                except (IndexError, Exception):
                    break

        # RSSI from RadioTap
        rssi = -70  # default
        if pkt.haslayer(RadioTap):
            rt = pkt[RadioTap]
            if hasattr(rt, "dBm_AntSignal"):
                rssi = rt.dBm_AntSignal

        gps = self.gps_func() if self.gps_func else None
        lat, lon = gps if gps else (None, None)

        return NetworkObservation(
            bssid=bssid,
            ssid=ssid,
            channel=channel,
            frequency=channel_to_freq(channel),
            rssi=rssi,
            security=detect_security(pkt),
            latitude=lat,
            longitude=lon,
        )   
