                        
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


**WtW** stands for **Watches the Watchers** and is a work-in-progress (WIP) simple wardriving tool.

At the moment, **only the passive module is being developed and actively worked on**.

Feel free to open issues, fork the repository, or contribute in any way you like. Please, however, use this tool only on networks you own or on networks for which you have explicit permission from the owner. I will not be held liable for any misuse of this software.

I’m open to collaborating with anyone interested.

**This software is provided as-is, without warranty of any kind. The author is not responsible for any illegal use or damage resulting from its use.**

This software is under MIT license. Just tag me.

**Status: early development / not ready for production use**

---

## The Modules

    ┌─────────────────────────────────────────────────────────┐
    │                    DASHBOARD (Web)                      │
    │         React/Vite + Leaflet + WebSocket                │
    │         ┌───────────────────────────────────┐           │
    │         │  Map view  │  Stats  │  Command   │           │
    │         └───────────────────────────────────┘           │
    └────────────────────────┬────────────────────────────────┘
                             │ WebSocket + REST
    ┌────────────────────────▼────────────────────────────────┐
    │              API (FastAPI / Rust Axum)                  │
    │   /api/networks  /api/stats  /ws/live  /cmd/activate    │
    └────────────────────────┬────────────────────────────────┘
                             │
    ┌────────────────────────▼────────────────────────────────┐
    │              PROCESSOR (pipeline)                       │
    │   parse → dedup → enrich (OUI, GPS) → store → broadcast │
    └────────────────────────┬────────────────────────────────┘
                             │
    ┌────────────────────────▼────────────────────────────────┐
    │         COLLECTOR (plugin system)  ← qui si estende     │
    │                                                         │
    │  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐   │
    │  │  Passive    │  │ Active-Deauth│  │ Handshake-    │   │
    │  │  Scanner    │  │  (future)    │  │ Capture(fut.) │   │
    │  │  (scapy /   │  │              │  │               │   │
    │  │  airodump)  │  │              │  │               │   │
    │  └─────────────┘  └──────────────┘  └───────────────┘   │
    │                                                         │
    │  Ogni modulo implementa la stessa interfaccia:          │
    │    start() / stop() / yield Packet()                    │
    └─────────────────────────────────────────────────────────┘

