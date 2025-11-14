import json
import psycopg2
import psycopg2.pool
from psycopg2.extras import execute_batch
from datetime import datetime
from typing import List, Tuple
import logging
import os
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- POSTGRESQL CONFIG ----------
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

class ShopperDataProcessor:
    def __init__(self, db_config: dict):
        """
        Initialize the processor with database configuration
        
        Args:
            db_config: Dictionary with keys: host, database, user, password, port
        """
        self.db_config = db_config
        self.connection = None
        self.db_pool = None
        self.zone_data = None

    def connect_to_db(self):
        # ---------- POSTGRESQL CLIENT ----------
        try:
            self.db_pool = psycopg2.pool.SimpleConnectionPool(
                1, 20,
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD
            )
            self.connection = self.db_pool.getconn()
            print("✅ PostgreSQL connection pool initialized")
        except Exception as e:
            print(f"⚠️  PostgreSQL connection failed: {e}")
            self.db_pool = None
    
    def close_connection(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")
    
    def parse_location(self, location_str: str) -> Tuple[int, int]:
        """
        Parse location string 'x,y' into separate x and y coordinates
        
        Args:
            location_str: String in format "x,y"
            
        Returns:
            Tuple of (x, y) as integers
        """
        try:
            x, y = location_str.split(',')
            return int(x), int(y)
        except (ValueError, AttributeError) as e:
            logger.error(f"Error parsing location '{location_str}': {e}")
            raise
    
    def parse_json_line(self, json_line: str) -> List[Tuple]:
        """
        Parse a single JSON line and extract shopper data
        
        Args:
            json_line: JSON string containing time and shoppers data
            
        Returns:
            List of tuples (time, shopper_id, x, y)
        """
        try:
            data = json.loads(json_line.strip())
            timestamp = datetime.fromisoformat(data['time'].replace('Z', '+00:00'))
            
            records = []
            for shopper in data['shoppers']:
                shopper_id = int(shopper['id'])
                x, y = self.parse_location(shopper['loc'])
                records.append((timestamp, shopper_id, x, y))
            
            if not data['shoppers']:
                records.append((timestamp, None, None, None))
            
            return records
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Error parsing JSON line '{json_line}': {e}")
            return []
    
    def process_file(self, file_path: str) -> List[Tuple]:
        """
        Process entire file and extract all shopper movement records
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            List of all records as tuples (time, shopper_id, x, y)
        """
        all_records = []
        
        try:
            with open(file_path, 'r') as file:
                for line_num, line in enumerate(file, 1):
                    if line.strip():  # Skip empty lines
                        records = self.parse_json_line(line)
                        all_records.extend(records)
                        
                        if line_num % 100 == 0:
                            logger.info(f"Processed {line_num} lines, {len(all_records)} total records")
            
            logger.info(f"Finished processing file. Total records: {len(all_records)}")
            return all_records
            
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            raise
        except Exception as e:
            logger.error(f"Error processing file: {e}")
            raise
    
    def load_zone_data(self) -> List[Tuple]:
        """
        Load zone dimension data from database once for in-memory calculations
        
        Returns:
            List of tuples (zone_id, x_min, x_max, y_min, y_max)
        """
        if not self.connection:
            raise Exception("Database connection not established")
        
        try:
            cursor = self.connection.cursor()
            query = "SELECT id, x_min, x_max, y_min, y_max FROM powerbi_data.zone_dim"
            cursor.execute(query)
            zone_data = cursor.fetchall()
            cursor.close()
            
            logger.info(f"Loaded {len(zone_data)} zones from database")
            return zone_data
            
        except psycopg2.Error as e:
            logger.error(f"Error loading zone data: {e}")
            raise

    def get_zone_id_from_coordinates(self, x: int, y: int, zone_data: List[Tuple]) -> int:
        """
        Calculate zone_id based on x, y coordinates using in-memory zone data
        
        Args:
            x: X coordinate
            y: Y coordinate  
            zone_data: List of zone tuples (zone_id, x_min, x_max, y_min, y_max)
            
        Returns:
            Zone ID that contains the given coordinates, or None if no zone found
        """
        for zone_id, x_min, x_max, y_min, y_max in zone_data:
            if x_min <= x <= x_max and y_min <= y <= y_max:
                return zone_id
        return None

    def insert_records(self, records: List[Tuple], batch_size: int = 1000):
        """
        Insert records into PostgreSQL database in batches
        
        Args:
            records: List of tuples (time, shopper_id, x, y)
            batch_size: Number of records to insert per batch
        """
        if not self.connection:
            raise Exception("Database connection not established")
        
        # Load zone data once for all calculations
        if not self.zone_data:
            self.zone_data = self.load_zone_data()
        
        insert_query = """
            INSERT INTO powerbi_data.camera_data (time, zone_id, shopper_id, x, y)
            VALUES (%s, %s, %s, %s, %s)
        """
        
        try:
            cursor = self.connection.cursor()
            
            # Insert records in batches
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                
                # Transform batch to include zone_id using in-memory zone data
                batch_with_zone = []
                for time, shopper_id, x, y in batch:
                    if x is not None and y is not None:
                        zone_id = self.get_zone_id_from_coordinates(x, y, self.zone_data)
                    else:
                        zone_id = None
                    batch_with_zone.append((time, zone_id, shopper_id, x, y))
                
                execute_batch(cursor, insert_query, batch_with_zone)
                self.connection.commit()
                logger.info(f"Inserted batch {i//batch_size + 1}: {len(batch)} records")
            
            logger.info(f"Successfully inserted {len(records)} total records")
            
        except psycopg2.Error as e:
            if self.connection:
                self.connection.rollback()
                logger.error(f"Error inserting records: {e}")
                raise
        finally:
            if self.connection:
                cursor.close()
                self.db_pool.putconn(self.connection)
    
    def process_and_store(self, file_path: str, batch_size: int = 1000):
        """
        Complete pipeline: process file and store in database
        
        Args:
            file_path: Path to the JSON file
            batch_size: Number of records to insert per batch
        """
        try:
            self.connect_to_db()
            records = self.process_file(file_path)
            self.insert_records(records, batch_size)
            logger.info("Data processing and storage completed successfully")
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            raise
        finally:
            self.close_connection()


def main():
    """Example usage of the ShopperDataProcessor"""
    
    # Database configuration
    db_config = {
        'host': DB_HOST,
        'database': DB_NAME,
        'user': DB_USER,
        'password': DB_PASSWORD,
        'port': DB_PORT
    }
    
    # Initialize processor
    processor = ShopperDataProcessor(db_config)
    
    # Process the file and store in database
    file_path = 'synthetic_shopper.txt'  # Update with your file path
    
    try:
        processor.process_and_store(file_path, batch_size=1000)
    except Exception as e:
        print(f"Processing failed: {e}")


if __name__ == "__main__":
    main()