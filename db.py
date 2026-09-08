#database

import sqlite3
import time

class wtwDB:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA journal_mode=WAL;") #ideally for sd cards
        self._create_tables()

    def _create_tables(self):
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS networks (
                bssid       TEXT PRIMARY KEY,
                ssid        TEXT,
                channel     INTEGER,
                security    TEXT,
                first_seen  REAL,
                last_seen   REAL
            );

            CREATE TABLE IF NOT EXISTS sightings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                bssid       TEXT NOT NULL,
                lat         REAL,
                lon         REAL,
                alt         REAL,
                rssi        INTEGER,
                timestamp   REAL NOT NULL,
                FOREIGN KEY (bssid) REFERENCES networks(bssid)
            );

            CREATE INDEX IF NOT EXISTS idx_sightings_bssid ON sightings(bssid);
            CREATE INDEX IF NOT EXISTS idx_sightings_ts ON sightings(timestamp);
        ''')
        self.conn.commit()

    def save_sighting(self, net, pos):
        #save network if not exists
        '''
        net = {'bssid': str, 'ssid': str, 'channel': int, 'security': str, 'rssi': int }
        pos = {'lat': float, 'lon': float, 'alt': float, 'sat': int }
        '''
        now = time.time()

        #add network if not exists or else update
        self.conn.execute('''
            INSERT INTO networks (bssid, ssid, channel, security, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(bssid) DO UPDATE SET
                ssid       = excluded.ssid,
                channel    = excluded.channel,
                security   = excluded.security,
                last_seen  = excluded.last_seen
        ''', (net['bssid'], net['ssid'], net['channel'], net['security'], now, now))

        #add sighting
        self.conn.execute('''
            INSERT INTO sightings (bssid, lat, lon, alt, rssi, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (net['bssid'], pos['lat'], pos['lon'], pos['alt'], net['rssi'], now))

        self.conn.commit()

    def get_stats(self):
        nets = self.conn.execute('SELECT COUNT(*) FROM networks').fetchone()[0]
        sights = self.conn.execute('SELECT COUNT(*) FROM sightings').fetchone()[0]
        return {'unique': nets, 'total': sights}

    def close(self):
        self.conn.commit()
        self.conn.close()
