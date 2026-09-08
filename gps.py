import socket
import json
import subprocess
import time
import logging

log = logging.getLogger("WtW")

class wtwGPS:
    def __init__(self, device):
        self.device = device
        self._sock = None
        self._last_data = None
        self._gpsd_proc = None

    def start(self):
        #check for conflicting gpsd processes
        check = subprocess.run(['systemctl', 'is-active', '--quiet', 'gpsd'], capture_output=True, text=True)

        if check.stdout.strip() == "active":
            subprocess.run(['sudo', 'systemctl', 'stop', 'gpsd'], capture_output=True)
            log.info("Stopped existing gpsd service to avoid conflicts.")

        # Start gpsd process on specify device connected with socket
        try:
            self.gpsd_proc = subprocess.Popen(
                ['sudo', 'gpsd', '-n', '-b', self.device],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            time.sleep(2)  # Give gpsd time to start

        except FileNotFoundError:
            log.error("gpsd not found. Please install gpsd.")
            self._sock=None
            return

        #connect to gpsd socket
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.connect(("127.0.0.1", 2947))
            self._sock.settimeout(5.0)
            log.info(f"Connected to gpsd on {self.device}")
        except (ConnectionRefusedError, OSError) as e:
            log.warning(f"Failed to connect to gpsd: {e}")
            self._sock = None
            return

    def get_position(self):
        """
        return a dict with lat, lon, alt, sat if not fix all 0 
        """
        if self._sock is None:
            return {"lat": 0, "lon": 0, "alt": 0, "sat": 0}

        try:
            # Request GPS data
            self._sock.sendall(b'{"class":"WATCH","enable":true,"json":true};\n')
            #request data
            self._sock.sendall(b'{"class":"POLL"};\n')

            data = self._sock.recv(4096).decode()

            # Parse JSON response
            for line in data.strip().split('\n'):
                if not line.strip():
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue
            #Time Position and Vwelocity (mode 3 = 3D fix)
                if msg.get("class") == "TPV" and msg.get("mode", 0) >=3:
                    self._last_data = msg
                    break

            if self._last_data:
                return {
                    "lat": self._last_data.get("lat", 0),
                    "lon": self._last_data.get("lon", 0),
                    "alt": self._last_data.get("alt", 0),
                    "sat": self._last_data.get("satellites", 0),
                }

        except (socket.timeout, ConnectionResetError, OSError) as e:
            log.warning(f"GPS socket error: {e}")

        #fallback if no data or error or 0
        if self._last_data:
            return {
                "lat": self._last_data.get("lat", 0),
                "lon": self._last_data.get("lon", 0),
                "alt": self._last_data.get("alt", 0),
                "sat": self._last_data.get("satellites", 0),
            }
        return {"lat": 0, "lon": 0, "alt": 0, "sat": 0}
        
    def stop(self):
        # Stop gpsd process and close socket
        if self._sock:
            try:
                self._sock.sendall(b'{"class":"WATCH","enable":false};\n')
                self._sock.close()
            except OSError:
                pass

        if self.gpsd_proc:
            self.gpsd_proc.terminate()
            try:
                self.gpsd_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.gpsd_proc.kill()

        log.info("Stopped gpsd and closed socket")
