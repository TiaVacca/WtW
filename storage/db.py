# storage/db.py
import sqlite3
from pathlib import Path
from typing import Optional

from collector.base import NetworkObservation

DB_PATH = Path("data/wardriver.db")


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS networks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            bssid       TEXT NOT NULL,
            ssid        TEXT NOT NULL DEFAULT '',
            channel     INTEGER NOT NULL,
            frequency   INTEGER NOT NULL,
            rssi        INTEGER NOT NULL,
            security    TEXT NOT NULL,
            latitude    REAL,
            longitude   REAL,
            first_seen  REAL NOT NULL,
            last_seen   REAL NOT NULL,
            sightings   INTEGER NOT NULL DEFAULT 1,
            UNIQUE(bssid, ssid)
        );

        CREATE INDEX IF NOT EXISTS idx_bssid ON networks(bssid);
        CREATE INDEX IF NOT EXISTS idx_location ON networks(latitude, longitude);
    """)
    conn.commit()
    conn.close()


def upsert(obs: NetworkObservation) -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO networks (bssid, ssid, channel, frequency, rssi,
                              security, latitude, longitude,
                              first_seen, last_seen, sightings)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        ON CONFLICT(bssid, ssid) DO UPDATE SET
            last_seen = excluded.last_seen,
            rssi = excluded.rssi,
            channel = excluded.channel,
            frequency = excluded.frequency,
            security = excluded.security,
            latitude = COALESCE(excluded.latitude, networks.latitude),
            longitude = COALESCE(excluded.longitude, networks.longitude),
            sightings = sightings + 1
    """, (
        obs.bssid, obs.ssid, obs.channel, obs.frequency,
        obs.rssi, obs.security, obs.latitude, obs.longitude,
        obs.timestamp, obs.timestamp,
    ))
    conn.commit()
    conn.close()


def get_all_networks() -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM networks ORDER BY last_seen DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats() -> dict:
    conn = sqlite3.connect(DB_PATH)
    total = conn.execute("SELECT COUNT(*) FROM networks").fetchone()[0]
    by_sec = conn.execute(
        "SELECT security, COUNT(*) as n FROM networks GROUP BY security"
    ).fetchall()
    conn.close()
    return {
        "total_networks": total,
        "by_security": {row[0]: row[1] for row in by_sec},
    }   