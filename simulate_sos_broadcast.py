import asyncio
import time
from datetime import datetime


class ANSI:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"


def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


async def broadcast_to_client(client_id: str, payload: dict, latency_ms: float):
    await asyncio.sleep(latency_ms / 1000.0)
    print(
        f"[{timestamp()}] {ANSI.GREEN}INFO{ANSI.RESET}  [WS_DISPATCH] Sent SOS frame to {ANSI.CYAN}{client_id:<18}{ANSI.RESET} | Ack Latency: {ANSI.BOLD}{latency_ms:.2f} ms{ANSI.RESET}"
    )
    return latency_ms


async def main():
    print(
        f"{ANSI.BOLD}{ANSI.WHITE}========================================================================================{ANSI.RESET}"
    )
    print(
        f"{ANSI.BOLD}{ANSI.CYAN}       CTG SHIELD BACKEND — GEOSPATIAL INTELLIGENCE & REAL-TIME SOS ENGINE              {ANSI.RESET}"
    )
    print(
        f"{ANSI.BOLD}{ANSI.WHITE}========================================================================================{ANSI.RESET}\n"
    )

    # 1. Server initialization & spatial index load
    print(
        f"[{timestamp()}] {ANSI.BLUE}INFO{ANSI.RESET}  [BOOT] Starting CTG-Shield Async Engine (FastAPI / WebSockets / PostGIS)"
    )
    await asyncio.sleep(0.3)
    print(
        f"[{timestamp()}] {ANSI.BLUE}INFO{ANSI.RESET}  [SPATIAL_INDEX] Loaded 14 Danger Zone Polygons into memory (Chittagong Grid)"
    )
    await asyncio.sleep(0.3)

    # 2. Simulate Active Responder WebSocket Connections
    clients = [
        ("RESP-PATROL-01", 1.14),
        ("RESP-POLICE-04", 1.82),
        ("USER-GUARDIAN-08", 2.35),
        ("RESP-PATROL-03", 0.95),
        ("USER-COMMUNITY-12", 3.10),
    ]

    for cid, _ in clients:
        print(
            f"[{timestamp()}] {ANSI.GREEN}INFO{ANSI.RESET}  [WS_SESSION] Client connected: {ANSI.CYAN}{cid}{ANSI.RESET} (Handshake 101 Switching Protocols)"
        )
        await asyncio.sleep(0.15)

    print(
        f"\n[{timestamp()}] {ANSI.GREEN}INFO{ANSI.RESET}  [SOCKET_POOL] Active listeners: {len(clients)} responders connected\n"
    )
    await asyncio.sleep(0.6)

    # 3. Emergency SOS Event Triggered
    sos_payload = {
        "event_id": "SOS-98214-CTG",
        "sender_id": "USER-VICTIM-99",
        "coordinates": {"lat": 22.3569, "lon": 91.7832},
        "accuracy_m": 4.2,
        "trigger_type": "PANIC_BUTTON_TAP_X3",
    }

    print(
        f"[{timestamp()}] {ANSI.RED}{ANSI.BOLD}[🚨 SOS EVENT RECEIVED]{ANSI.RESET} Incoming panic payload from {ANSI.YELLOW}{sos_payload['sender_id']}{ANSI.RESET}"
    )
    print(
        f"[{timestamp()}] {ANSI.YELLOW}DEBUG{ANSI.RESET} Coordinates: ({sos_payload['coordinates']['lat']}, {sos_payload['coordinates']['lon']}) | Accuracy: {sos_payload['accuracy_m']}m"
    )

    # 4. PostGIS Polygon Danger-Zone Spatial Intersection Query
    t0 = time.perf_counter()
    await asyncio.sleep(0.008)  # simulate sub-millisecond PostGIS query
    spatial_time_ms = (time.perf_counter() - t0) * 1000
    print(
        f"[{timestamp()}] {ANSI.BLUE}INFO{ANSI.RESET}  [POSTGIS] ST_Contains() query evaluated in {ANSI.BOLD}{spatial_time_ms:.2f} ms{ANSI.RESET} -> Zone: {ANSI.RED}ZONE-RED-AGRABAD-03{ANSI.RESET} (Risk Score: 0.89)"
    )

    # 5. Async WebSocket Broadcast
    print(
        f"[{timestamp()}] {ANSI.RED}{ANSI.BOLD}[BROADCAST_START]{ANSI.RESET} Fan-out dispatching to {len(clients)} nearby registered endpoints..."
    )
    t_broadcast = time.perf_counter()

    tasks = [
        broadcast_to_client(cid, sos_payload, lat) for cid, lat in clients
    ]
    latencies = await asyncio.gather(*tasks)

    total_broadcast_ms = (time.perf_counter() - t_broadcast) * 1000

    # 6. Final Performance Telemetry Box
    avg_latency = sum(latencies) / len(latencies)
    print(
        f"\n{ANSI.BOLD}{ANSI.WHITE}+--------------------------------------------------------------------------------------+{ANSI.RESET}"
    )
    print(
        f"{ANSI.BOLD}{ANSI.WHITE}| {ANSI.GREEN}⚡ SOS BROADCAST TELEMETRY SUMMARY{ANSI.RESET}{' ' * 47}{ANSI.BOLD}{ANSI.WHITE}|{ANSI.RESET}"
    )
    print(
        f"{ANSI.BOLD}{ANSI.WHITE}+--------------------------------------------------------------------------------------+{ANSI.RESET}"
    )
    print(
        f"{ANSI.BOLD}{ANSI.WHITE}| Total Endpoints Reached : {ANSI.CYAN}{len(clients)} clients{' ' * 47}{ANSI.BOLD}{ANSI.WHITE}|{ANSI.RESET}"
    )
    print(
        f"{ANSI.BOLD}{ANSI.WHITE}| Spatial Query Latency   : {ANSI.GREEN}{spatial_time_ms:.2f} ms{' ' * 51}{ANSI.BOLD}{ANSI.WHITE}|{ANSI.RESET}"
    )
    print(
        f"{ANSI.BOLD}{ANSI.WHITE}| Average Client Latency  : {ANSI.GREEN}{avg_latency:.2f} ms{' ' * 51}{ANSI.BOLD}{ANSI.WHITE}|{ANSI.RESET}"
    )
    print(
        f"{ANSI.BOLD}{ANSI.WHITE}| Total Async Fan-out Time: {ANSI.GREEN}{total_broadcast_ms:.2f} ms{' ' * 51}{ANSI.BOLD}{ANSI.WHITE}|{ANSI.RESET}"
    )
    print(
        f"{ANSI.BOLD}{ANSI.WHITE}+--------------------------------------------------------------------------------------+{ANSI.RESET}\n"
    )


if __name__ == "__main__":
    asyncio.run(main())