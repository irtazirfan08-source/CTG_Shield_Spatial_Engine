"""
CTG Shield - FastAPI Gateway with PostGIS Spatial Engine, Heatmap & Proximity SOS
"""
from fastapi.middleware.cors import CORSMiddleware
import sys
import os
import asyncio
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db_service.connect()
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
    """
    Triggers instant SOS broadcast to all active nearby users within the radius.
    """
    try:
        # 1. Log incident automatically into database
        await db_service.log_incident(
            incident_type="ASSAULT",
            description=f"EMERGENCY SOS Triggered by {payload.user_name} ({payload.emergency_type})",
            longitude=payload.longitude,
            latitude=payload.latitude,
            reporter_id=None
        )

        # 2. Broadcast alarm payload to all users within radius
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
    """
    Two-way real-time socket connection:
    - Client sends periodic GPS pings: {"lon": 91.8220, "lat": 22.3600}
    - Server pushes instant proximity sirens if an SOS occurs nearby
    """
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
    @app.get("/init-db")
async def initialize_database():
    """Create required spatial tables and populate initial Chittagong risk zones."""
    create_table_sql = """
    CREATE EXTENSION IF NOT EXISTS postgis;
    
    CREATE TABLE IF NOT EXISTS ctg_risk_zones (
        id SERIAL PRIMARY KEY,
        zone_name VARCHAR(100) NOT NULL,
        risk_level VARCHAR(20) NOT NULL,
        base_risk_score FLOAT DEFAULT 0.5,
        location GEOMETRY(Point, 4326),
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
        latitude FLOAT,
        longitude FLOAT,
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Insert seed spatial hotspots around Chittagong if table is empty
    INSERT INTO ctg_risk_zones (zone_name, risk_level, base_risk_score, location, radius_meters, description)
    SELECT 'GEC Circle', 'HIGH', 0.85, ST_SetSRID(ST_MakePoint(91.8215, 22.3569), 4326), 600, 'Heavy congestion, evening snatching hotspot'
    WHERE NOT EXISTS (SELECT 1 FROM ctg_risk_zones WHERE zone_name = 'GEC Circle');

    INSERT INTO ctg_risk_zones (zone_name, risk_level, base_risk_score, location, radius_meters, description)
    SELECT 'Agrabad Commercial Area', 'MEDIUM', 0.55, ST_SetSRID(ST_MakePoint(91.8122, 22.3275), 4326), 800, 'Financial district, pickpocket risk during peak hours'
    WHERE NOT EXISTS (SELECT 1 FROM ctg_risk_zones WHERE zone_name = 'Agrabad Commercial Area');

    INSERT INTO ctg_risk_zones (zone_name, risk_level, base_risk_score, location, radius_meters, description)
    SELECT '2 No Gate', 'HIGH', 0.78, ST_SetSRID(ST_MakePoint(91.8229, 22.3685), 4326), 500, 'Dense intersection and high vehicle transit'
    WHERE NOT EXISTS (SELECT 1 FROM ctg_risk_zones WHERE zone_name = '2 No Gate');

    INSERT INTO ctg_risk_zones (zone_name, risk_level, base_risk_score, location, radius_meters, description)
    SELECT 'Chawkbazar', 'MEDIUM', 0.60, ST_SetSRID(ST_MakePoint(91.8385, 22.3578), 4326), 600, 'Student and market gathering point'
    WHERE NOT EXISTS (SELECT 1 FROM ctg_risk_zones WHERE zone_name = 'Chawkbazar');
    """
    
    if hasattr(db_service, 'pool') and db_service.pool:
        async with db_service.pool.acquire() as conn:
            await conn.execute(create_table_sql)
        return {"status": "success", "message": "Database tables and spatial risk zones created successfully!"}
    else:
        return {"status": "error", "message": "Database connection pool not ready"}