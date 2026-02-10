# Author: Brian Ngo 10/11/2025
# Email: ngbao128@gmail.com
#!/usr/bin/env python3
"""
Sensor data handling module
"""

import json
import os
import time
import threading
import boto3
import psycopg2
import psycopg2.pool
from awscrt import io, mqtt, auth, http
from awsiot import mqtt_connection_builder
from dotenv import load_dotenv

load_dotenv()

# ---------- ENVIRONMENT VARIABLES ----------
S3_BUCKET = os.getenv("S3_BUCKET")
S3_SENSOR_PREFIX = os.getenv("S3_SENSOR_PREFIX")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# ---------- IOT CONFIG ----------
IOT_SENSOR_ENDPOINT = os.getenv("IOT_SENSOR_ENDPOINT")
SENSOR_CLIENT_ID = os.getenv("SENSOR_CLIENT_ID")
SENSOR_TOPIC = os.getenv("SENSOR_TOPIC")
PATH_TO_CERT = "certs/sensor/device.pem.crt"
PATH_TO_KEY = "certs/sensor/private.pem.key"
PATH_TO_ROOT = "certs/sensor/AmazonRootCA1.pem"

class SensorDataHandler:
    def __init__(self):
        self.s3 = self._init_s3()
        self.db_pool = self._init_postgres()
        self.mqtt_connection = None
        self.received_count = 0
        self.received_all_event = threading.Event()
        
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
            timestamp = payload.get('timestamp_ms') if isinstance(payload, dict) else None
            filename = f"{S3_SENSOR_PREFIX}message_{timestamp}.json"
                
            self.s3.put_object(
                Bucket=S3_BUCKET, 
                Key=filename, 
                Body=json.dumps(payload),
                ContentType='application/json'
            )
            print(f"✅ Uploaded to S3: s3://{S3_BUCKET}/{filename}")
        except Exception as e:
            print(f"❌ S3 upload failed: {e}")
    
    def save_to_postgres(self, payload):
        """Save IoT message to PostgreSQL sensor_data table."""
        if self.db_pool is None:
            print("❌ PostgreSQL pool not available - skipping database save")
            return
            
        connection = None
        try:
            connection = self.db_pool.getconn()
            cursor = connection.cursor()
            
            # Extract sensor data from payload
            thing = payload.get('thing', None)
            temperature_c = payload.get('temperature_C', None)
            pressure_hpa = payload.get('pressure_hPa', None)
            humidity_rh = payload.get('humidity_RH', None)
            
            # Get timestamp
            timestamp_ms = payload.get('timestamp_ms') if isinstance(payload, dict) else None
            
            # Insert into powerbi_data.sensor_data table
            if timestamp_ms:
                cursor.execute(
                    "INSERT INTO powerbi_data.sensor_data (thing, temperature_c, pressure_hpa, humidity_rh, time) VALUES (%s, %s, %s, %s, to_timestamp(%s))",
                    (thing, temperature_c, pressure_hpa, humidity_rh, timestamp_ms / 1000)
                )
            else:
                cursor.execute(
                    "INSERT INTO powerbi_data.sensor_data (thing, temperature_c, pressure_hpa, humidity_rh, time) VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)",
                    (thing, temperature_c, pressure_hpa, humidity_rh)
                )
            
            connection.commit()
            print(f"✅ Saved to PostgreSQL: {cursor.rowcount} row(s) inserted")
            
        except Exception as e:
            print(f"❌ PostgreSQL save failed: {e}")
            if connection:
                connection.rollback()
        finally:
            if connection:
                cursor.close()
                self.db_pool.putconn(connection)
    
    def process_sensor_data(self, payload):
        """Process sensor data by saving to both S3 and PostgreSQL."""
        self.save_to_s3(payload)
        self.save_to_postgres(payload)
    
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
                message_json = {"message": message_str, "type": "text"}
            
            # Process sensor data
            self.process_sensor_data(message_json)
            
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
            endpoint=IOT_SENSOR_ENDPOINT,
            cert_filepath=PATH_TO_CERT,
            pri_key_filepath=PATH_TO_KEY,
            client_bootstrap=client_bootstrap,
            ca_filepath=PATH_TO_ROOT,
            client_id=SENSOR_CLIENT_ID,
            clean_session=False,
            keep_alive_secs=30,
            on_connection_interrupted=self.on_connection_interrupted,
            on_connection_resumed=self.on_connection_resumed
        )
        
        print(f"🔗 Connecting to {IOT_SENSOR_ENDPOINT} with client ID '{SENSOR_CLIENT_ID}'...")
        
        # Connect with timeout
        connect_future = self.mqtt_connection.connect()
        connect_result = connect_future.result(timeout=10)  # 10 second timeout
        print(f"✅ Connected! Session present: {connect_result['session_present']}")
        
        return self.mqtt_connection

    def subscribe_to_topic(self):
        """Subscribe to the MQTT topic."""
        print(f"📡 Subscribing to topic: {SENSOR_TOPIC}")
        
        subscribe_future, packet_id = self.mqtt_connection.subscribe(
            topic=SENSOR_TOPIC,
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=self.on_message_received
        )
        
        subscribe_result = subscribe_future.result(timeout=10)
        print(f"✅ Subscribed to '{SENSOR_TOPIC}' with QoS: {subscribe_result['qos']}")

    def display_stats(self):
        """Display connection statistics."""
        print(f"📊 Messages received: {self.received_count}")
        print(f"📡 Listening on topic: {SENSOR_TOPIC}")
        if self.s3:
            print(f"💾 S3 storage: s3://{S3_BUCKET}/{S3_SENSOR_PREFIX}")
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
            
            # Connect to IoT
            self.connect_to_iot()
            
            # Subscribe to topic
            self.subscribe_to_topic()
            
            # Display initial stats
            self.display_stats()
            
            # Keep running and listening
            print("🔄 Listening for messages... (Press Ctrl+C to stop)")
            print(f"💡 Waiting for messages on topic '{SENSOR_TOPIC}'...")
            
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
    sensor_handler = SensorDataHandler()
    return sensor_handler.run()


if __name__ == "__main__":
    exit(main())