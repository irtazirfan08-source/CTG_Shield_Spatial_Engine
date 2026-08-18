"""
CTG Shield - FastAPI Gateway with PostGIS Spatial Engine, Heatmap & Proximity SOS
"""
import sys
import os
import asyncio
from contextlib import asynccontextmanager
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import uvicorn
import asyncpg

from spatial_service import SpatialSafetyService
from sos_dispatcher import ProximitySOSDispatcher

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

DB_USER = os.getenv("DB_USER", "ctg_user")
DB_PASS = os.getenv("DB_PASS", "nY7PGhRreB0e8WiYkWbrMdrGaLevCDOF")
DB_NAME = os.getenv("DB_NAME", "ctg_shield")
DB_HOST = os.getenv("DB_HOST", "dpg-da0k1ss9v7es739i6690-a")
DB_PORT = os.getenv("DB_PORT", "5432")

db_service = SpatialSafetyService(
    db_user=DB_USER,
    db_pass=DB_PASS,
    db_name=DB_NAME,
    db_host=DB_HOST,
    db_port=DB_PORT
)
sos_dispatcher = ProximitySOSDispatcher()

global_pool: Optional[asyncpg.Pool] = None


async def run_db_migrations():
    """Auto-migrate tables and ensure all spatial tables exist."""
    global global_pool
    if not global_pool:
        return

    migration_sql = """
    CREATE EXTENSION IF NOT EXISTS postgis;
    
    CREATE TABLE IF NOT EXISTS ctg_risk_zones (
        id SERIAL PRIMARY KEY,
        zone_name VARCHAR(100) NOT NULL,
        thana VARCHAR(100) DEFAULT 'General',
        dominant_crime_type VARCHAR(100) DEFAULT 'General Safety Alert',
        risk_level VARCHAR(20) NOT NULL,
        base_risk_score FLOAT DEFAULT 0.5,
        peak_start_hour INT DEFAULT 18,
        peak_end_hour INT DEFAULT 23,
        location GEOMETRY(Point, 4326),
        boundary GEOMETRY(Geometry, 4326),
        radius_meters FLOAT DEFAULT 500.0,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS incidents (
        id SERIAL PRIMARY KEY,
        incident_type VARCHAR(50) NOT NULL,
        description TEXT,
        severity VARCHAR(20) DEFAULT 'medium',
        location GEOMETRY(Point, 4326),
        reporter_id VARCHAR(100),
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    UPDATE ctg_risk_zones SET 
        thana = 'Khulshi', 
        dominant_crime_type = 'Mugging & Snatching',
        peak_start_hour = 19,
        peak_end_hour = 23,
        base_risk_score = 0.85,
        radius_meters = 600.0,
        location = ST_SetSRID(ST_MakePoint(91.8215, 22.3569), 4326),
        boundary = ST_Buffer(ST_SetSRID(ST_MakePoint(91.8215, 22.3569), 4326)::geography, 600.0)::geometry
    WHERE zone_name = 'GEC Circle';

    UPDATE ctg_risk_zones SET 
        thana = 'Double Mooring', 
        dominant_crime_type = 'Pickpocketing & Theft',
        peak_start_hour = 17,
        peak_end_hour = 21,
        base_risk_score = 0.55,
        radius_meters = 800.0,
        location = ST_SetSRID(ST_MakePoint(91.8122, 22.3275), 4326),
        boundary = ST_Buffer(ST_SetSRID(ST_MakePoint(91.8122, 22.3275), 4326)::geography, 800.0)::geometry
    WHERE zone_name = 'Agrabad Commercial Area';

    UPDATE ctg_risk_zones SET 
        thana = 'Panchlaish', 
        dominant_crime_type = 'Evening Snatching & Harassment',
        peak_start_hour = 20,
        peak_end_hour = 24,
        base_risk_score = 0.78,
        radius_meters = 500.0,
        location = ST_SetSRID(ST_MakePoint(91.8229, 22.3685), 4326),
        boundary = ST_Buffer(ST_SetSRID(ST_MakePoint(91.8229, 22.3685), 4326)::geography, 500.0)::geometry
    WHERE zone_name = '2 No Gate';

    UPDATE ctg_risk_zones SET 
        thana = 'Chawkbazar', 
        dominant_crime_type = 'Overcrowding & Harassment',
        peak_start_hour = 16,
        peak_end_hour = 22,
        base_risk_score = 0.60,
        radius_meters = 600.0,
        location = ST_SetSRID(ST_MakePoint(91.8385, 22.3578), 4326),
        boundary = ST_Buffer(ST_SetSRID(ST_MakePoint(91.8385, 22.3578), 4326)::geography, 600.0)::geometry
    WHERE zone_name = 'Chawkbazar';
    """
    async with global_pool.acquire() as conn:
        await conn.execute(migration_sql)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global global_pool
    global_pool = await asyncpg.create_pool(
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        host=DB_HOST,
        port=DB_PORT,
        min_size=2,
        max_size=10
    )
    await db_service.connect()
    await run_db_migrations()
    yield
    if global_pool:
        await global_pool.close()
    await db_service.close()


app = FastAPI(
    title="CTG Shield - Urban Safety & Proximity SOS Engine",
    description="Real-time geographic crime-zone intelligence & proximity alarm system for Chittagong.",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Schemas ---

class IncidentReportRequest(BaseModel):
    incident_type: str = Field(..., description="MUGGING, ROBBERY, HARASSMENT, ASSAULT, or HAZARD")
    description: str = Field(..., description="Brief details about what happened")
    longitude: float = Field(..., description="GPS Longitude (e.g., 91.8220)")
    latitude: float = Field(..., description="GPS Latitude (e.g., 22.3600)")


class SOSTriggerRequest(BaseModel):
    user_id: str = Field(..., description="Unique User ID of victim")
    user_name: str = Field(..., description="Victim's name")
    user_phone: str = Field(..., description="Victim's contact phone")
    longitude: float = Field(..., description="Victim's current GPS Longitude")
    latitude: float = Field(..., description="Victim's current GPS Latitude")
    emergency_type: str = Field(default="PHYSICAL_ATTACK", description="ATTACK, MUGGING, ACCIDENT, HARASSMENT")
    broadcast_radius_meters: float = Field(default=2500.0, description="Broadcast radius in meters")


# --- HTTP Endpoints ---

@app.get("/")
def root():
    return {
        "system": "CTG Shield Unified Safety Platform",
        "city": "Chittagong, Bangladesh",
        "status": "Operational",
        "spatial_db": "PostgreSQL 16 + PostGIS",
        "realtime_engine": "Proximity WebSocket Dispatcher"
    }


@app.get("/init-db")
async def initialize_database():
    await run_db_migrations()
    return {"status": "success", "message": "Database schema updated successfully!"}


@app.get("/api/v1/incidents/recent")
async def get_recent_incidents(limit: int = 50):
    """Retrieve all reported incidents directly with PostGIS coordinates."""
    global global_pool
    if not global_pool:
        raise HTTPException(status_code=500, detail="Database pool not ready.")

    query = """
    SELECT 
        id, 
        incident_type, 
        description, 
        COALESCE(severity, 'medium') as severity, 
        ST_Y(location::geometry) as latitude, 
        ST_X(location::geometry) as longitude, 
        created_at 
    FROM incidents 
    WHERE location IS NOT NULL
    ORDER BY id DESC 
    LIMIT $1;
    """
    try:
        async with global_pool.acquire() as conn:
            rows = await conn.fetch(query, limit)
            return [
                {
                    "id": r["id"],
                    "incident_type": r["incident_type"],
                    "description": r["description"] or "",
                    "severity": r["severity"],
                    "latitude": float(r["latitude"]) if r["latitude"] is not None else 0.0,
                    "longitude": float(r["longitude"]) if r["longitude"] is not None else 0.0,
                    "created_at": r["created_at"].isoformat() if r["created_at"] else None
                }
                for r in rows
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query error: {str(e)}")


@app.get("/api/v1/safety/evaluate-location")
async def evaluate_user_location(
    lon: float = Query(..., description="User's current GPS Longitude"),
    lat: float = Query(..., description="User's current GPS Latitude"),
    simulated_hour: Optional[int] = Query(None, description="Optional: Test specific hour (0-23)")
):
    try:
        return await db_service.check_user_risk_status(longitude=lon, latitude=lat, check_hour=simulated_hour)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/incidents/report")
async def report_incident(payload: IncidentReportRequest):
    global global_pool
    if not global_pool:
        raise HTTPException(status_code=500, detail="Database pool not ready.")
    try:
        insert_sql = """
        INSERT INTO incidents (incident_type, description, location, status)
        VALUES ($1, $2, ST_SetSRID(ST_MakePoint($3, $4), 4326), 'active')
        RETURNING id;
        """
        async with global_pool.acquire() as conn:
            report_id = await conn.fetchval(
                insert_sql,
                payload.incident_type.upper(),
                payload.description,
                payload.longitude,
                payload.latitude
            )
            return {
                "status": "SUCCESS",
                "message": "Incident reported and recorded in spatial ledger.",
                "incident_id": report_id
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/sos/trigger")
async def trigger_emergency_sos(payload: SOSTriggerRequest):
    global global_pool
    if not global_pool:
        raise HTTPException(status_code=500, detail="Database pool not ready.")
    try:
        insert_sql = """
        INSERT INTO incidents (incident_type, description, location, status, severity)
        VALUES ('ASSAULT', $1, ST_SetSRID(ST_MakePoint($2, $3), 4326), 'active', 'high')
        RETURNING id;
        """
        async with global_pool.acquire() as conn:
            await conn.fetchval(
                insert_sql,
                f"EMERGENCY SOS Triggered by {payload.user_name} ({payload.emergency_type})",
                payload.longitude,
                payload.latitude
            )

        broadcast_result = await sos_dispatcher.broadcast_emergency_alarm(
            victim_user_id=payload.user_id,
            victim_name=payload.user_name,
            victim_phone=payload.user_phone,
            longitude=payload.longitude,
            latitude=payload.latitude,
            emergency_type=payload.emergency_type,
            radius_meters=payload.broadcast_radius_meters
        )

        return broadcast_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/safety-stream/{user_id}")
async def websocket_safety_stream(websocket: WebSocket, user_id: str):
    await sos_dispatcher.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if "lon" in data and "lat" in data:
                sos_dispatcher.update_location(
                    user_id=user_id,
                    longitude=float(data["lon"]),
                    latitude=float(data["lat"])
                )
    except WebSocketDisconnect:
        sos_dispatcher.disconnect(user_id)


@app.get("/simulator", response_class=HTMLResponse)
def get_sos_simulator():
    with open("simulator.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/map", response_class=HTMLResponse)
def get_safety_map():
    with open("map.html", "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)