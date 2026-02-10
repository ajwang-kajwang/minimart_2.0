# Author: Brian Ngo 10/11/2025
# Email: ngbao128@gmail.com
#!/usr/bin/env python3
"""
Camera data handling module
"""

import json
import os
import time
import threading
import boto3
import psycopg2
import psycopg2.pool
from psycopg2.extras import execute_batch
from awscrt import io, mqtt, auth, http
from awsiot import mqtt_connection_builder
from dotenv import load_dotenv
from datetime import datetime
from typing import List, Tuple
import logging

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- ENVIRONMENT VARIABLES ----------
S3_BUCKET = os.getenv("S3_BUCKET")
S3_CAMERA_PREFIX = os.getenv("S3_CAMERA_PREFIX", "camera/")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# ---------- IOT CONFIG ----------
IOT_CAMERA_ENDPOINT = os.getenv("IOT_CAMERA_ENDPOINT")
CAMERA_CLIENT_ID = os.getenv("CAMERA_CLIENT_ID")
CAMERA_TOPIC = os.getenv("CAMERA_TOPIC")
PATH_TO_CERT = "certs/camera/device.pem.crt"
PATH_TO_KEY = "certs/camera/private.pem.key"
PATH_TO_ROOT = "certs/camera/AmazonRootCA1.pem"

class CameraDataHandler:
    def __init__(self):
        self.s3 = self._init_s3()
        self.db_pool = self._init_postgres()
        self.mqtt_connection = None
        self.received_count = 0
        self.received_all_event = threading.Event()
        self.zone_data = None
        
    def _init_s3(self):
        """Initialize S3 client."""
        try:
            s3 = boto3.client("s3")
            print("✅ S3 client initialized")
            return s3
        except Exception as e:
            print(f"⚠️  S3 client failed to initialize: {e}")
            return None
    
    def _init_postgres(self):
        """Initialize PostgreSQL connection pool."""
        try:
            db_pool = psycopg2.pool.SimpleConnectionPool(
                1, 20,
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD
            )
            print("✅ PostgreSQL connection pool initialized")
            return db_pool
        except Exception as e:
            print(f"⚠️  PostgreSQL connection failed: {e}")
            return None
    
    def save_to_s3(self, payload):
        """Upload IoT message to S3 as JSON file."""
        if self.s3 is None:
            print("❌ S3 client not available - skipping upload")
            return
            
        try:
            timestamp = payload.get('time') if isinstance(payload, dict) else None
            if timestamp:
                # Convert timestamp to filename-safe format
                timestamp_safe = timestamp.replace(':', '-').replace('T', '_').replace('Z', '')
                filename = f"{S3_CAMERA_PREFIX}message_{timestamp_safe}.json"
            else:
                filename = f"{S3_CAMERA_PREFIX}message_{int(time.time() * 1000)}.json"
                
            self.s3.put_object(
                Bucket=S3_BUCKET, 
                Key=filename, 
                Body=json.dumps(payload),
                ContentType='application/json'
            )
            print(f"✅ Uploaded to S3: s3://{S3_BUCKET}/{filename}")
        except Exception as e:
            print(f"❌ S3 upload failed: {e}")
    
    def load_zone_data(self):
        """Load zone dimension data from database once for in-memory calculations."""
        if self.db_pool is None:
            print("❌ PostgreSQL pool not available - cannot load zone data")
            return []
            
        connection = None
        try:
            connection = self.db_pool.getconn()
            cursor = connection.cursor()
            query = "SELECT id, x_min, x_max, y_min, y_max FROM powerbi_data.zone_dim"
            cursor.execute(query)
            zone_data = cursor.fetchall()
            cursor.close()
            
            logger.info(f"Loaded {len(zone_data)} zones from database")
            return zone_data
            
        except psycopg2.Error as e:
            logger.error(f"Error loading zone data: {e}")
            return []
        finally:
            if connection:
                self.db_pool.putconn(connection)

    def get_zone_id_from_coordinates(self, x: int, y: int) -> int:
        """Calculate zone_id based on x, y coordinates using in-memory zone data."""
        if not self.zone_data:
            return None
            
        for zone_id, x_min, x_max, y_min, y_max in self.zone_data:
            if x_min <= x <= x_max and y_min <= y <= y_max:
                return zone_id
        return None

    def parse_location(self, location_str: str) -> Tuple[int, int]:
        """Parse location string 'x,y' into separate x and y coordinates."""
        try:
            x, y = location_str.split(',')
            return round(float(x)), round(float(y))
        except (ValueError, AttributeError) as e:
            logger.error(f"Error parsing location '{location_str}': {e}")
            raise

    def parse_camera_data(self, payload) -> List[Tuple]:
        """Parse camera data payload and extract shopper movement records."""
        try:
            if isinstance(payload, str):
                data = json.loads(payload)
            else:
                data = payload
                
            # Parse timestamp
            timestamp_str = data.get('time')
            if timestamp_str:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                timestamp = datetime.now()
            
            records = []
            shoppers = data.get('shoppers', [])
            
            for shopper in shoppers:
                shopper_id = int(shopper['id'])
                x, y = self.parse_location(shopper['loc'])
                zone_id = self.get_zone_id_from_coordinates(x, y)
                records.append((timestamp, shopper_id, zone_id, x, y))
            
            # If no shoppers, still record timestamp
            if not shoppers:
                records.append((timestamp, None, None, None, None))
            
            return records
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Error parsing camera data: {e}")
            return []

    def save_to_postgres(self, records: List[Tuple]):
        """Save camera data records to PostgreSQL camera_data table."""
        if self.db_pool is None:
            print("❌ PostgreSQL pool not available - skipping database save")
            return
            
        if not records:
            print("❌ No records to save")
            return
            
        connection = None
        try:
            connection = self.db_pool.getconn()
            cursor = connection.cursor()
            
            insert_query = """
                INSERT INTO powerbi_data.camera_data (time, shopper_id, zone_id, x, y)
                VALUES (%s, %s, %s, %s, %s)
            """
            
            execute_batch(cursor, insert_query, records)
            connection.commit()
            
            print(f"✅ Saved to PostgreSQL: {len(records)} record(s) inserted")
            
        except Exception as e:
            print(f"❌ PostgreSQL save failed: {e}")
            if connection:
                connection.rollback()
        finally:
            if connection:
                cursor.close()
                self.db_pool.putconn(connection)
    
    def process_camera_data(self, payload):
        """Process camera data by saving to both S3 and PostgreSQL."""
        # Save raw data to S3
        self.save_to_s3(payload)
        
        # Parse and save processed data to PostgreSQL
        records = self.parse_camera_data(payload)
        if records:
            self.save_to_postgres(records)
    
    def on_connection_interrupted(self, connection, error, **kwargs):
        """Callback when connection is interrupted."""
        print(f"🔌 Connection interrupted. Error: {error}")

    def on_connection_resumed(self, connection, return_code, session_present, **kwargs):
        """Callback when connection is resumed."""
        print(f"🔌 Connection resumed. Return code: {return_code}, Session present: {session_present}")

    def on_message_received(self, topic, payload, dup, qos, retain, **kwargs):
        """Handle incoming MQTT messages."""
        self.received_count += 1
        
        try:
            # Decode payload
            message_str = payload.decode('utf-8')
            print(f"📨 Message #{self.received_count} on '{topic}': {message_str}")
            
            # Try to parse as JSON
            try:
                message_json = json.loads(message_str)
                print(f"📄 Parsed JSON: {json.dumps(message_json, indent=2)}")
            except json.JSONDecodeError:
                print("📄 Message is not JSON - treating as plain text")
                message_json = {"message": message_str, "type": "text", "time": datetime.now().isoformat()}
            
            # Process camera data
            self.process_camera_data(message_json)
            
        except Exception as e:
            print(f"❌ Error processing message: {e}")

    def connect_to_iot(self):
        """Establish connection to AWS IoT Core."""
        print("🚀 Initializing AWS IoT connection...")
        
        # Create event loop group
        event_loop_group = io.EventLoopGroup(1)
        host_resolver = io.DefaultHostResolver(event_loop_group)
        client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)
        
        # Build MQTT connection
        self.mqtt_connection = mqtt_connection_builder.mtls_from_path(
            endpoint=IOT_CAMERA_ENDPOINT,
            cert_filepath=PATH_TO_CERT,
            pri_key_filepath=PATH_TO_KEY,
            client_bootstrap=client_bootstrap,
            ca_filepath=PATH_TO_ROOT,
            client_id=CAMERA_CLIENT_ID,
            clean_session=False,
            keep_alive_secs=30,
            on_connection_interrupted=self.on_connection_interrupted,
            on_connection_resumed=self.on_connection_resumed
        )
        
        print(f"🔗 Connecting to {IOT_CAMERA_ENDPOINT} with client ID '{CAMERA_CLIENT_ID}'...")
        
        # Connect with timeout
        connect_future = self.mqtt_connection.connect()
        connect_result = connect_future.result(timeout=10)  # 10 second timeout
        print(f"✅ Connected! Session present: {connect_result['session_present']}")
        
        return self.mqtt_connection

    def subscribe_to_topic(self):
        """Subscribe to the MQTT topic."""
        print(f"📡 Subscribing to topic: {CAMERA_TOPIC}")
        
        subscribe_future, packet_id = self.mqtt_connection.subscribe(
            topic=CAMERA_TOPIC,
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=self.on_message_received
        )
        
        subscribe_result = subscribe_future.result(timeout=10)
        print(f"✅ Subscribed to '{CAMERA_TOPIC}' with QoS: {subscribe_result['qos']}")

    def display_stats(self):
        """Display connection statistics."""
        print(f"📊 Messages received: {self.received_count}")
        print(f"📡 Listening on topic: {CAMERA_TOPIC}")
        if self.s3:
            print(f"💾 S3 storage: s3://{S3_BUCKET}/{S3_CAMERA_PREFIX}")
        else:
            print("💾 S3 storage: Not configured")
        
        if self.db_pool:
            print(f"🐘 PostgreSQL: Connected to {DB_HOST}:{DB_PORT}/{DB_NAME}")
        else:
            print("🐘 PostgreSQL: Not configured")

    def verify_certificates(self):
        """Verify certificate files exist."""
        cert_files = [PATH_TO_CERT, PATH_TO_KEY, PATH_TO_ROOT]
        for cert_file in cert_files:
            if not os.path.exists(cert_file):
                print(f"❌ Certificate file not found: {cert_file}")
                return False
        return True

    def disconnect_mqtt(self):
        """Disconnect from MQTT."""
        if self.mqtt_connection:
            print("🔌 Disconnecting...")
            try:
                disconnect_future = self.mqtt_connection.disconnect()
                disconnect_future.result(timeout=5)
                print("✅ Disconnected successfully")
            except Exception as e:
                print(f"⚠️  Disconnect error (not critical): {e}")

    def close(self):
        """Close all connections."""
        # Disconnect MQTT
        self.disconnect_mqtt()
        
        # Close database connections
        if self.db_pool:
            print("🐘 Closing database connections...")
            try:
                self.db_pool.closeall()
                print("✅ Database connections closed")
            except Exception as e:
                print(f"⚠️  Database close error (not critical): {e}")

    def run(self):
        """Main run method to start the IoT client."""
        try:
            # Verify certificate files exist
            if not self.verify_certificates():
                return 1
            
            # Load zone data for coordinate processing
            self.zone_data = self.load_zone_data()
            if not self.zone_data:
                print("⚠️  Warning: No zone data loaded - zone_id will be None for all records")
            
            # Connect to IoT
            self.connect_to_iot()
            
            # Subscribe to topic
            self.subscribe_to_topic()
            
            # Display initial stats
            self.display_stats()
            
            # Keep running and listening
            print("🔄 Listening for messages... (Press Ctrl+C to stop)")
            print(f"💡 Waiting for camera messages on topic '{CAMERA_TOPIC}'...")
            
            # Display stats every 30 seconds
            last_stats_time = time.time()
            
            try:
                while True:
                    time.sleep(1)
                    
                    # Show stats every 30 seconds
                    current_time = time.time()
                    if current_time - last_stats_time >= 30:
                        print(f"\n📊 Status Update - Messages received: {self.received_count}")
                        last_stats_time = current_time
                        
            except KeyboardInterrupt:
                print(f"\n👋 Shutting down...")
                print(f"📊 Final stats: {self.received_count} messages processed")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return 1
            
        finally:
            self.close()
        
        return 0


def main():
    """Main function to run the camera data handler."""
    camera_handler = CameraDataHandler()
    return camera_handler.run()


if __name__ == "__main__":
    exit(main())