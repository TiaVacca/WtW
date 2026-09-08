#!/usr/bin/env python3
#da rimuovere per renderlo eseguibile scrivendo solo ./main.py senza specificare di usare python

"""
                                          
                                          
           .---.    ___             .---. 
          /. ./|  ,--.'|_          /. ./| 
      .--'.  ' ;  |  | :,'     .--'.  ' ; 
     /__./ \ : |  :  : ' :    /__./ \ : | 
 .--'.  '   \  ..;__,'  / .--'.  '   \ . 
/___/ \ |    ' '|  |   | /___/ \ |    ' ' 
;   \  \;      ::__,'| : ;   \  \;      : 
 \   ;  `      |  '  : |__\   ;  `      | 
  .   \    .\  ;  |  | '.'|.   \    .\  ; 
   \   \   ' \ |  ;  :    ; \   \   ' \ | 
    :   '  |--"   |  ,   /   :   '  |--"  
     \   \ ;       ---`-'     \   \ ;     
      '---"                    '---"      
                                          
"""

#di servizio
import sys
import time
import logging
import argparse
import signal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("WtW")

#argomenti specificabili da cli
def parse_args():
    p = argparse.ArgumentParser(description="WtW - Watching the Watchers")
    p.add_argument("--mode", choices=["passive", "active"], default="passive", help="Scan Mode (default: passive)")
    p.add_argument("--iface", default="wlan0", help="Network interface to use (default: wlan0)")
    p.add_argument("--gps", default="/dev/ttyUSB0", help="GPS device (default: /dev/ttyUSB0)")
    p.add_argument("--db", default="wtw.db", help="Database file (default: wtw.db)")
    p.add_argument("--interval", type=int, default=5, help="Scan interval in seconds (default: 5)")
    p.add_argument("--export", action="store_true", help="Export file CVS and GPX")

    return p.parse_args()

def main():
    args = parse_args()
    log.info(f"Starting WtW in {args.mode.upper} mode on interface {args.iface} with GPS {args.gps} and database {args.db}")

    #starting things from args
    db = wtwDB(args.db)
    gps = wtwGPS(args.gps)
    scanner = wtwScanner(args.iface)

    #handling things so it not close wrong
    running = True
    def stop(sig, frame):
        nonlocal running
        log.info("Stopping WtW...")
        running = False

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    #starting
    try:
        gps.start()
        scanner.start()
        log.info("WtW started. Press Ctrl+C to stop.")

        while running:
            #net discovered
            networks = scanner.get_networks()

            #read position
            pos = gps.get_position()

            #save to db
            for net in networks:
                db.save_sighting(net, pos)

            #for a later night
            if args.mode == "active":
                #TODO: deauth capture handshake...
                pass

            #log
            log.info(f"Net discovered: {len(networks)} | GPS: {pos['lat']:.5f},{pos['lon']:.5f} ({pos['sat']} sat)")

            time.sleep(args.interval)

    #when closing
    finally:
        scanner.stop()
        gps.stop()

        if args.export:
            from exporter import export_csv, export_gpx
            export_csv(db, "wtw_export.csv")
            export_gpx(db, "wtw_export.gpx")
            log.info("Exported data to wtw_export.csv and wtw_export.gpx")

        stats = db.get_stats()
        log.info(f"Scan Statistics: {stats['total']} total sightings, {stats['unique']} unique networks")
        db.close()

    log.info("WtW stopped.")

if __name__ == "__main__":
    main()
    