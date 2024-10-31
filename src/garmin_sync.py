import logging
from garminconnect import Garmin
import sqlite3
from datetime import datetime, timedelta
import os
from typing import Optional, List, Dict
import json

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")


class GarminWeightTracker:
    """Class to fetch and store weight data from Garmin Connect."""

    def __init__(
        self,
        email: str,
        password: str,
        db_path: str = "/app/data/weight_data.db",
        token_file: str = "/app/data/garmin_token.json",
    ):
        """Initialize the tracker with database and token paths."""
        self.email = email
        self.password = password
        self.client = None
        self.db_path = db_path
        self.token_file = token_file

        self._db = sqlite3.connect(self.db_path)
        self.setup_database()

    def setup_database(self):
        """Create the database and table if they don't exist."""
        with self._db as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS weight_measurements (
                    timestamp INTEGER PRIMARY KEY,
                    date TEXT NOT NULL,
                    weight REAL NOT NULL,
                    bmi REAL,
                    body_fat REAL,
                    body_water REAL,
                    bone_mass REAL,
                    muscle_mass REAL,
                    physique_rating TEXT,
                    visceral_fat REAL,
                    metabolic_age INTEGER,
                    source_type TEXT,
                    created_at INTEGER NOT NULL,
                    source TEXT
                )
            """
            )

    def connect_to_garmin(self) -> Optional[Garmin]:
        """Connect to Garmin Connect API."""
        try:
            logging.info("Connecting to Garmin Connect")
            client = Garmin(self.email, self.password)

            # Try to load existing token
            try:
                if os.path.exists(self.token_file):
                    logging.info("Loading saved token")
                    client.login(self.token_file)
                    # Verify the token is still valid
                    client.get_full_name()
                    logging.info("Loaded valid token")
                    self.client = client
                    return client
            except:
                logging.info("Saved token expired, logging in again")

            # Login and save new token
            client.login()
            client.garth.dump(self.token_file)
            logging.info("Connected to Garmin Connect and saved token")
            self.client = client
            return client
        except Exception as e:
            logging.error(f"Failed to connect to Garmin: {e}")
            return None

    def get_weight_data(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Fetch weight data from Garmin Connect within the given date range."""
        weight_data = []
        date = start_date
        while date <= end_date:
            logging.debug(f"Fetching weight data for {date.date()}")
            data = self.client.get_body_composition(date.isoformat()[:10])

            if data and "dateWeightList" in data:
                for entry in data["dateWeightList"]:
                    measurement_timestamp = entry[
                        "date"
                    ]  # This is the Garmin timestamp
                    weight_data.append(
                        {
                            "timestamp": measurement_timestamp,
                            "date": datetime.fromtimestamp(
                                measurement_timestamp / 1000
                            ).strftime("%Y-%m-%d"),
                            "weight": entry.get("weight", None),
                            "bmi": entry.get("bmi", None),
                            "body_fat": entry.get("bodyFat", None),
                            "body_water": entry.get("bodyWater", None),
                            "bone_mass": entry.get("boneMass", None),
                            "muscle_mass": entry.get("muscleMass", None),
                            "physique_rating": entry.get("physiqueRating", None),
                            "visceral_fat": entry.get("visceralFat", None),
                            "metabolic_age": entry.get("metabolicAge", None),
                            "source_type": entry.get("sourceType", None),
                        }
                    )

                logging.debug(
                    f"Fetched {len(data['dateWeightList'])} weight measurements for {date.date()}"
                )
            else:
                logging.debug(f"No weight data found for {date.date()}")
            date += timedelta(days=1)
        return weight_data

    def fetch_and_store_weight(self, start_date: datetime, end_date: datetime):
        """Fetch weight data from Garmin and store in SQLite."""
        # Fetch weight data
        logging.info(
            f"Fetching weight data from {start_date.date()} to {end_date.date()}"
        )
        weight_data = self.get_weight_data(start_date, end_date)

        # Store in database
        logging.info(f"Storing {len(weight_data)} weight measurements in the database")
        with self._db as conn:
            for measurement in weight_data:
                logging.info(f"Storing {measurement}")
                conn.execute(
                    """
                    INSERT OR IGNORE INTO weight_measurements 
                    (timestamp, date, weight, bmi, body_fat, body_water, bone_mass, 
                    muscle_mass, physique_rating, visceral_fat, metabolic_age, 
                    source_type, created_at, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        measurement["timestamp"],
                        measurement["date"],
                        measurement["weight"],
                        measurement["bmi"],
                        measurement["body_fat"],
                        measurement["body_water"],
                        measurement["bone_mass"],
                        measurement["muscle_mass"],
                        measurement["physique_rating"],
                        measurement["visceral_fat"],
                        measurement["metabolic_age"],
                        measurement["source_type"],
                        int(datetime.now().timestamp()),
                        "garmin",
                    ),
                )
            conn.commit()
            logging.info(
                f"Total rows in database: {conn.execute('SELECT COUNT(*) FROM weight_measurements').fetchone()[0]}"
            )

        logging.info("Successfully stored weight data")

    def get_earliest_weight_data(self) -> Optional[datetime]:
        """Get the earliest date for which weight data is available.

        Searches backwards in 30-day chunks and stops when it finds 60 consecutive
        days with no data, assuming this means we've gone past all historical data.
        Also stores all data as it's fetched.
        """
        try:
            current_date = datetime.now() - timedelta(days=30)  # Start from 30 days ago
            empty_days_count = 0
            earliest_timestamp = None

            while (
                empty_days_count < 60
            ):  # Stop if we find 60 consecutive days with no data
                chunk_end = current_date + timedelta(days=30)
                logging.info(
                    f"Fetching and storing data from {current_date.date()} to {chunk_end.date()}"
                )

                data = self.client.get_body_composition(current_date.isoformat()[:10])

                if data and "dateWeightList" in data and data["dateWeightList"]:
                    # Store the data we got
                    self.fetch_and_store_weight(current_date, chunk_end)

                    # Found some data, reset empty days counter
                    empty_days_count = 0
                    # Update earliest timestamp if we found earlier data
                    chunk_earliest = min(
                        entry["date"] for entry in data["dateWeightList"]
                    )
                    if (
                        earliest_timestamp is None
                        or chunk_earliest < earliest_timestamp
                    ):
                        earliest_timestamp = chunk_earliest
                else:
                    empty_days_count += 30

                current_date -= timedelta(days=30)  # Move backwards by 30 days
                logging.debug(
                    f"Checking date: {current_date.date()}, Empty days: {empty_days_count}"
                )

            return (
                datetime.fromtimestamp(earliest_timestamp / 1000)
                if earliest_timestamp
                else None
            )
        except Exception as e:
            logging.error(f"Error finding earliest weight date: {e}")
            return None
