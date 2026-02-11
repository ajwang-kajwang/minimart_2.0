#!/bin/bash
set -e

echo "Setting up database with custom schemas and users..."

# Create schemas and setup database structure
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Create schemas
    CREATE SCHEMA IF NOT EXISTS powerbi_data;

    CREATE USER powerbi_user WITH PASSWORD '$POWERBI_USER_PASSWORD';

    -- Create sensor_data table in powerbi_data schema
    CREATE TABLE IF NOT EXISTS powerbi_data.sensor_data (
        id SERIAL PRIMARY KEY,
        thing TEXT,
        temperature_c NUMERIC,
        pressure_hpa NUMERIC,
        humidity_rh NUMERIC,
        time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Create index on sensor_data
    CREATE INDEX idx_sensor_data_thing ON powerbi_data.sensor_data(thing);
    CREATE INDEX idx_sensor_data_time ON powerbi_data.sensor_data(time);

    -- Create zone_dim in powerbi_data schema
    DROP TABLE IF EXISTS powerbi_data.zone_dim;
    CREATE TABLE IF NOT EXISTS powerbi_data.zone_dim (
        id SERIAL PRIMARY KEY,
        zone_name CHAR(10) NOT NULL,
        x_min INTEGER,
        x_max INTEGER,
        y_min INTEGER,
        y_max INTEGER
    );
    -- Insert data in zone_dim
    INSERT INTO powerbi_data.zone_dim
    VALUES (1, 'Zone 1', 0, 16, 57, 100),
            (2, 'Zone 2', 43, 60, 57, 100),
            (3, 'Zone 3', 87, 100, 57, 100),
            (4, 'Zone 4', 87, 100, 0, 44),
            (5, 'Zone 5', 43, 60, 0, 44),
            (6, 'Counter', 0, 16, 0, 44),
            (7, 'Shelf 1', 17, 42, 0, 44),
            (8, 'Shelf 2', 61, 86, 0, 44),
            (9, 'Shelf 3', 17, 42, 57, 100),
            (10, 'Shelf 4', 61, 86, 57, 100),
            (11, 'Aisle', 0, 100, 45, 56);

    -- Create camera_data table in powerbi_data schema
    DROP TABLE IF EXISTS powerbi_data.camera_data;
    CREATE TABLE IF NOT EXISTS powerbi_data.camera_data (
        id SERIAL PRIMARY KEY,
        time TIMESTAMP WITH TIME ZONE NOT NULL,
        shopper_id INTEGER,
        zone_id INTEGER,
        x INTEGER,
        y INTEGER,
        FOREIGN KEY (zone_id) REFERENCES powerbi_data.zone_dim(id)
    );

    -- Add indexes for better query performance
    CREATE INDEX idx_camera_data_time ON powerbi_data.camera_data(time);
    CREATE INDEX idx_camera_data_shopper_id ON powerbi_data.camera_data(shopper_id);
    CREATE INDEX idx_camera_data_shopper_time ON powerbi_data.camera_data(shopper_id, time);


    -- Create the heatmap view 
    CREATE OR REPLACE VIEW powerbi_data.heatmap_view AS
    WITH 
    -- Generate all coordinates from 0 to 100
    coordinate_grid AS (
        SELECT x_coord, y_coord
        FROM generate_series(0, 100) AS x_coord
        CROSS JOIN generate_series(0, 100) AS y_coord
    ),
    -- Add zone_id to each coordinate based on zone boundaries
    coordinate_grid_with_zones AS (
        SELECT 
            cg.x_coord,
            cg.y_coord,
            zd.id as zone_id,
            zd.zone_name
        FROM coordinate_grid cg
        LEFT JOIN powerbi_data.zone_dim zd 
            ON cg.x_coord >= zd.x_min 
            AND cg.x_coord <= zd.x_max 
            AND cg.y_coord >= zd.y_min 
            AND cg.y_coord <= zd.y_max
    ),
    -- Count people at each location
    location_counts AS (
        SELECT 
            x,
            y,
            zone_id,
            COUNT(DISTINCT shopper_id) as ppl_count
        FROM powerbi_data.camera_data
        WHERE x BETWEEN 0 AND 100 
        AND y BETWEEN 0 AND 100
        GROUP BY x, y, zone_id
    )
    -- Join grid with counts, filling missing locations with 0
    SELECT 
        cgz.x_coord as x,
        cgz.y_coord as y,
        cgz.zone_id,
        cgz.zone_name,
        COALESCE(lc.ppl_count, 0) as ppl_count
    FROM coordinate_grid_with_zones cgz
    LEFT JOIN location_counts lc 
        ON cgz.x_coord = lc.x 
        AND cgz.y_coord = lc.y 
        AND cgz.zone_id = lc.zone_id
    ORDER BY x, y;

    -- Grant permissions to powerbi_user on powerbi_data schema
    GRANT USAGE ON SCHEMA powerbi_data TO powerbi_user;
    GRANT SELECT ON ALL TABLES IN SCHEMA powerbi_data TO powerbi_user;
EOSQL

echo "Database setup completed successfully!"