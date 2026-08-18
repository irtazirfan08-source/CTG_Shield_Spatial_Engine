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

from spatial_service import SpatialSafetyService
from sos_dispatcher import ProximitySOSDispatcher

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Database configuration for local and cloud (Render)
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


def get_db_pool():
    """Dynamically resolve connection pool from SpatialSafetyService."""
    for attr in ['pool', '_pool', 'db_pool', 'connection_pool']:
        p = getattr(db_service, attr, None)
        if p is not None:
            return p
    return None


async def run_db_migrations():
    """Auto-migrate tables and ensure all spatial and incident columns exist."""
    pool = get_db_pool()
    if not pool:
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

    ALTER TABLE ctg_risk_zones ADD COLUMN IF NOT EXISTS thana VARCHAR(100) DEFAULT 'General';
    ALTER TABLE ctg_risk_zones ADD COLUMN IF NOT EXISTS dominant_crime_type VARCHAR(100) DEFAULT 'General Safety Alert';
    ALTER TABLE ctg_risk_zones ADD COLUMN IF NOT EXISTS base_risk_score FLOAT DEFAULT 0.5;
    ALTER TABLE ctg_risk_zones ADD COLUMN IF NOT EXISTS peak_start_hour INT DEFAULT 18;
    ALTER TABLE ctg_risk_zones ADD COLUMN IF NOT EXISTS peak_end_hour INT DEFAULT 23;
    ALTER TABLE ctg_risk_zones ADD COLUMN IF NOT EXISTS radius_meters FLOAT DEFAULT 500.0;
    ALTER TABLE ctg_risk_zones ADD COLUMN IF NOT EXISTS description TEXT;
    ALTER TABLE ctg_risk_zones ADD COLUMN IF NOT EXISTS location GEOMETRY(Point, 4326);
    ALTER TABLE ctg_risk_zones ADD COLUMN IF NOT EXISTS boundary GEOMETRY(Geometry, 4326);

    CREATE TABLE IF NOT EXISTS incidents (
        id SERIAL PRIMARY KEY,
        incident_type VARCHAR(50) NOT NULL,
        description TEXT,
        severity VARCHAR(20) DEFAULT 'medium',
        location GEOMETRY(Point, 4326),
        latitude FLOAT,
        longitude FLOAT,
        reporter_id VARCHAR(100),
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    ALTER TABLE incidents ADD COLUMN IF NOT EXISTS latitude FLOAT;
    ALTER TABLE incidents ADD COLUMN IF NOT EXISTS longitude FLOAT;
    ALTER TABLE incidents ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active';
    ALTER TABLE incidents ADD COLUMN IF NOT EXISTS reporter_id VARCHAR(100);
    ALTER TABLE incidents ADD COLUMN IF NOT EXISTS severity VARCHAR(20) DEFAULT 'medium';
    ALTER TABLE incidents ADD COLUMN IF NOT EXISTS location GEOMETRY(Point, 4326);

    UPDATE incidents 
    SET latitude = ST_Y(location::geometry), 
        longitude = ST_X(location::geometry) 
    WHERE (latitude IS NULL OR longitude IS NULL) AND location IS NOT NULL;

    UPDATE incidents SET status = 'active' WHERE status IS NULL;
    """
    async with pool.acquire() as conn:
        await conn.execute(migration_sql)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db_service.connect()
    await run_db_migrations()
    yield
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
    """Manual trigger to re-run database migrations."""
    await run_db_migrations()
    return {"status": "success", "message": "Database schema updated successfully!"}


@app.get("/api/v1/incidents/recent")
async def get_recent_incidents(limit: int = 50):
    """Retrieve recent reported incidents with coordinates from PostGIS."""
    pool = get_db_pool()
    if not pool:
        raise HTTPException(status_code=500, detail="Database connection pool unavailable.")

    query = """
    SELECT 
        id, 
        incident_type, 
        description, 
        severity, 
        COALESCE(latitude, ST_Y(location::geometry), 0.0) as latitude, 
        COALESCE(longitude, ST_X(location::geometry), 0.0) as longitude, 
        created_at 
    FROM incidents 
    ORDER BY id DESC 
    LIMIT $1;
    """
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, limit)
            return [
                {
                    "id": r["id"],
                    "incident_type": r["incident_type"] or "INCIDENT",
                    "description": r["description"] or "",
                    "severity": r["severity"] or "medium",
                    "latitude": float(r["latitude"]),
                    "longitude": float(r["longitude"]),
                    "created_at": r["created_at"].isoformat() if r["created_at"] else None
                }
                for r in rows
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    try:
        pool = get_db_pool()
        if pool:
            insert_sql = """
            INSERT INTO incidents (incident_type, description, location, latitude, longitude, status)
            VALUES ($1, $2, ST_SetSRID(ST_MakePoint($3, $4), 4326), $4, $3, 'active')
            RETURNING id;
            """
            async with pool.acquire() as conn:
                report_id = await conn.fetchval(
                    insert_sql,
                    payload.incident_type.upper(),
                    payload.description,
                    payload.longitude,
                    payload.latitude
                )
        else:
            report_id = await db_service.log_incident(
                incident_type=payload.incident_type.upper(),
                description=payload.description,
                longitude=payload.longitude,
                latitude=payload.latitude
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
    try:
        pool = get_db_pool()
        if pool:
            insert_sql = """
            INSERT INTO incidents (incident_type, description, location, latitude, longitude, status, severity)
            VALUES ('ASSAULT', $1, ST_SetSRID(ST_MakePoint($2, $3), 4326), $3, $2, 'active', 'high')
            RETURNING id;
            """
            async with pool.acquire() as conn:
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


# --- Real-Time WebSocket Channel ---

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


# --- Visual Dashboards ---

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