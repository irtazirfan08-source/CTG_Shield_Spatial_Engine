"""
Real-Time SOS Dispatcher & In-Memory Spatial Proximity Engine
Tracks active user locations and broadcasts emergency alerts to nearby responders.
"""

import math
import time
from typing import Dict, List, Any
from fastapi import WebSocket


class ProximitySOSDispatcher:
    def __init__(self):
        # Active WebSocket connections: {user_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}
        # Active user coordinates: {user_id: {"lon": float, "lat": float, "last_ping": float}}
        self.user_locations: Dict[str, Dict[str, Any]] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        """Registers a user's live WebSocket connection."""
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        """Removes a user when disconnected."""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if user_id in self.user_locations:
            del self.user_locations[user_id]

    def update_location(self, user_id: str, longitude: float, latitude: float):
        """Updates in-memory live GPS coordinates for a connected user."""
        self.user_locations[user_id] = {
            "longitude": longitude,
            "latitude": latitude,
            "last_ping": time.time()
        }

    @staticmethod
    def calculate_haversine_distance(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
        """
        Calculates great-circle distance between two GPS coordinates in meters.
        """
        R = 6371000  # Radius of Earth in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2.0) ** 2 + \
            math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    async def broadcast_emergency_alarm(
        self,
        victim_user_id: str,
        victim_name: str,
        victim_phone: str,
        longitude: float,
        latitude: float,
        emergency_type: str = "PHYSICAL_ATTACK",
        radius_meters: float = 2000.0
    ) -> Dict[str, Any]:
        """
        Identifies all active responders within the danger radius and pushes an instant alert payload.
        """
        alerted_users: List[Dict[str, Any]] = []

        alarm_payload = {
            "event": "CRITICAL_PROXIMITY_ALARM",
            "victim": {
                "id": victim_user_id,
                "name": victim_name,
                "phone": victim_phone
            },
            "location": {
                "longitude": longitude,
                "latitude": latitude,
                "google_maps_link": f"https://www.google.com/maps?q={latitude},{longitude}"
            },
            "emergency_type": emergency_type,
            "timestamp": int(time.time()),
            "siren_trigger": True
        }

        # Scan active users and calculate spatial proximity
        for responder_id, loc in self.user_locations.items():
            if responder_id == victim_user_id:
                continue  # Do not echo alert to the victim themselves

            distance = self.calculate_haversine_distance(
                longitude, latitude,
                loc["longitude"], loc["latitude"]
            )

            # Check if within danger alert radius (default 2km)
            if distance <= radius_meters:
                ws = self.active_connections.get(responder_id)
                if ws:
                    personalized_payload = {
                        **alarm_payload,
                        "distance_from_victim_meters": round(distance, 1)
                    }
                    try:
                        await ws.send_json(personalized_payload)
                        alerted_users.append({
                            "user_id": responder_id,
                            "distance_meters": round(distance, 1),
                            "delivery_status": "DELIVERED"
                        })
                    except Exception:
                        alerted_users.append({
                            "user_id": responder_id,
                            "distance_meters": round(distance, 1),
                            "delivery_status": "FAILED"
                        })

        return {
            "status": "SOS_BROADCAST_COMPLETED",
            "victim_id": victim_user_id,
            "total_responders_alerted": len(alerted_users),
            "alerted_responders": alerted_users
        }