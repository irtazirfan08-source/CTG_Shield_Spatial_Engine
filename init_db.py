import psycopg2

DATABASE_URL = "postgresql://ctg_user:nY7PGhRreB0e8WiYkWbrMdrGaLevCDOF@dpg-da0k1ss9v7es739i6690-a.singapore-postgres.render.com/ctg_shield"

queries = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        full_name VARCHAR(100) NOT NULL,
        phone_number VARCHAR(20) UNIQUE NOT NULL,
        emergency_contact VARCHAR(20) NOT NULL,
        hashed_password TEXT NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS incident_reports (
        id SERIAL PRIMARY KEY,
        reporter_id VARCHAR(255) DEFAULT 'anonymous',
        incident_type VARCHAR(255),
        description TEXT,
        latitude DOUBLE PRECISION,
        longitude DOUBLE PRECISION,
        location geometry(Point, 4326),
        geom geometry(Point, 4326),
        severity VARCHAR(50) DEFAULT 'medium',
        status VARCHAR(50) DEFAULT 'active',
        verified_status VARCHAR(50) DEFAULT 'pending',
        is_verified BOOLEAN DEFAULT FALSE,
        occurred_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_incident_reports_location 
    ON incident_reports USING GIST (location);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_incident_reports_geom 
    ON incident_reports USING GIST (geom);
    """
]

try:
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cursor = conn.cursor()
    for query in queries:
        cursor.execute(query)
    print("SUCCESS: Database schema updated with users table!")
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")