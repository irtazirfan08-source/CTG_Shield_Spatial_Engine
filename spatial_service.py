"""
Chittagong Safety Spatial Engine - PostGIS Database Service
Handles spatial polygon checks, proximity queries, and danger scoring.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
import asyncpg


class SpatialSafetyService:
    def __init__(self, db_user: str = "postgres", db_pass: str = "ctg_secure_pass_2026", db_host: str = "localhost", db_port: int = 5432, db_name: str = "ctg_safety_db"):
        self.dsn = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Initializes the database connection pool."""
        self.pool = await asyncpg.create_pool(self.dsn, min_size=2, max_size=10)

    async def close(self):
        """Closes all database connections."""
        if self.pool:
            await self.pool.close()

    async def check_user_risk_status(self, longitude: float, latitude: float, check_hour: Optional[int] = None) -> Dict[str, Any]:
        """
        Evaluates risk score by checking polygon boundaries and nearby incident density.
        """
        if check_hour is None:
            check_hour = datetime.now().hour

        async with self.pool.acquire() as conn:
            # 1. Check if user is inside a high-alert zone polygon during its active peak hours
            zone_query = """
                SELECT zone_name, thana, risk_level, dominant_crime_type, peak_start_hour, peak_end_hour
                FROM ctg_risk_zones
                WHERE ST_Contains(boundary, ST_SetSRID(ST_MakePoint($1, $2), 4326))
                  AND (
                      (peak_start_hour <= peak_end_hour AND $3 BETWEEN peak_start_hour AND peak_end_hour)
                      OR
                      (peak_start_hour > peak_end_hour AND ($3 >= peak_start_hour OR $3 <= peak_end_hour))
                  )
                LIMIT 1;
            """
            active_zone = await conn.fetchrow(zone_query, longitude, latitude, check_hour)

            # 2. Count verified incidents within a 1.5 km radius in the last 30 days
            incident_query = """
                SELECT COUNT(*) as incident_count
                FROM incident_reports
                WHERE ST_DWithin(
                    location::geography,
                    ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography,
                    1500
                )
                AND occurred_at >= NOW() - INTERVAL '30 days';
            """
            nearby_incidents = await conn.fetchval(incident_query, longitude, latitude)

            # Calculate composite danger score (0 - 100)
            base_score = 10
            if active_zone:
                level = active_zone["risk_level"]
                base_score += 65 if level == "CRITICAL" else (45 if level == "HIGH" else 20)
            
            base_score += min((nearby_incidents or 0) * 10, 25)
            final_score = min(base_score, 100)

            return {
                "danger_score": final_score,
                "risk_level_tag": "CRITICAL" if final_score >= 75 else ("HIGH" if final_score >= 50 else ("MODERATE" if final_score >= 25 else "LOW")),
                "is_in_active_risk_zone": active_zone is not None,
                "active_zone_details": dict(active_zone) if active_zone else None,
                "nearby_incidents_count_30d": nearby_incidents or 0,
                "coordinates": {"longitude": longitude, "latitude": latitude},
                "evaluated_hour": check_hour
            }

    async def log_incident(self, incident_type: str, description: str, longitude: float, latitude: float, reporter_id: Optional[str] = None) -> str:
        """Inserts a new crowdsourced incident report with PostGIS Point geometry."""
        async with self.pool.acquire() as conn:
            query = """
                INSERT INTO incident_reports (reporter_id, incident_type, description, location, occurred_at, verified_status)
                VALUES ($1, $2, $3, ST_SetSRID(ST_MakePoint($4, $5), 4326), NOW(), 'VERIFIED')
                RETURNING id;
            """
            incident_id = await conn.fetchval(query, reporter_id, incident_type, description, longitude, latitude)
            return str(incident_id)

    async def get_nearby_incidents(self, longitude: float, latitude: float, radius_meters: int = 2000) -> List[Dict[str, Any]]:
        """Retrieves all incidents within a given radius in meters."""
        async with self.pool.acquire() as conn:
            query = """
                SELECT 
                    id,
                    incident_type,
                    description,
                    occurred_at,
                    ROUND(ST_Distance(
                        location::geography, 
                        ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography
                    )) AS distance_meters
                FROM incident_reports
                WHERE ST_DWithin(
                    location::geography,
                    ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography,
                    $3
                )
                ORDER BY distance_meters ASC;
            """
            rows = await conn.fetch(query, longitude, latitude, radius_meters)
            return [
                {
                    "id": str(r["id"]),
                    "incident_type": r["incident_type"],
                    "description": r["description"],
                    "occurred_at": r["occurred_at"].isoformat(),
                    "distance_meters": r["distance_meters"]
                }
                for r in rows
            ]