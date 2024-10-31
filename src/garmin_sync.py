import logging
from garminconnect import Garmin
import sqlite3
from datetime import datetime, timedelta
import os
from typing import Optional, List, Dict, TypedDict, Union
import json

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")


class WeightMeasurement(TypedDict):
    """Type definition for weight measurement data."""

    timestamp: int
    date: str
    weight: float
    bmi: Optional[float]
    body_fat: Optional[float]
    body_water: Optional[float]
    bone_mass: Optional[float]
    muscle_mass: Optional[float]
    physique_rating: Optional[str]
    visceral_fat: Optional[float]
    metabolic_age: Optional[int]
    source_type: Optional[str]


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

    def get_weight_data(
        self, start_date: datetime, end_date: datetime
    ) -> List[WeightMeasurement]:
        """Fetch weight data from Garmin Connect within the given date range."""
        weight_data: List[WeightMeasurement] = []
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
                        WeightMeasurement(
                            timestamp=measurement_timestamp,
                            date=datetime.fromtimestamp(
                                measurement_timestamp / 1000
                            ).strftime("%Y-%m-%d"),
                            weight=entry.get("weight", None),
                            bmi=entry.get("bmi", None),
                            body_fat=entry.get("bodyFat", None),
                            body_water=entry.get("bodyWater", None),
                            bone_mass=entry.get("boneMass", None),
                            muscle_mass=entry.get("muscleMass", None),
                            physique_rating=entry.get("physiqueRating", None),
                            visceral_fat=entry.get("visceralFat", None),
                            metabolic_age=entry.get("metabolicAge", None),
                            source_type=entry.get("sourceType", None),
                        )
                    )

                logging.debug(
                    f"Fetched {len(data['dateWeightList'])} weight measurements for {date.date()}"
                )
            else:
                logging.debug(f"No weight data found for {date.date()}")
            date += timedelta(days=1)
        return weight_data

    def serialize_weight_measurement(self, measurement: WeightMeasurement) -> tuple:
        """Convert a WeightMeasurement into a tuple for database insertion."""
        return (
            measurement["timestamp"],
            measurement["date"],
            measurement["weight"],
            measurement.get("bmi"),
            measurement.get("body_fat"),
            measurement.get("body_water"),
            measurement.get("bone_mass"),
            measurement.get("muscle_mass"),
            measurement.get("physique_rating"),
            measurement.get("visceral_fat"),
            measurement.get("metabolic_age"),
            measurement.get("source_type"),
            int(datetime.now().timestamp()),
            "garmin",
        )

    def _process_garmin_data(
        self, data_list: List[WeightMeasurement]
    ) -> tuple[Optional[int], int]:
        """Process and store Garmin weight data.

        Args:
            data_list: List of weight measurements from Garmin API

        Returns:
            tuple: (earliest_timestamp, count_of_records)
        """
        earliest_timestamp = None
        records_count = 0

        for measurement in data_list:
            timestamp = measurement["timestamp"]
            if earliest_timestamp is None or timestamp < earliest_timestamp:
                earliest_timestamp = timestamp

            with self._db as conn:
                for measurement in data_list:
                    logging.info(f"Storing {measurement}")
                    conn.execute(
                        """
                            INSERT OR IGNORE INTO weight_measurements 
                        (timestamp, date, weight, bmi, body_fat, body_water, bone_mass, 
                        muscle_mass, physique_rating, visceral_fat, metabolic_age, 
                        source_type, created_at, source)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        self.serialize_weight_measurement(measurement),
                    )
            conn.commit()
            logging.info(
                f"Total rows in database: {conn.execute('SELECT COUNT(*) FROM weight_measurements').fetchone()[0]}"
            )
            records_count += 1

        return earliest_timestamp, records_count

    def fetch_and_store_weight(self, start_date: datetime, end_date: datetime) -> int:
        """Fetch weight data from Garmin and store it in the database.

        Returns:
            int: Number of records stored
        """
        data = self.get_weight_data(start_date, end_date)
        _, records_count = self._process_garmin_data(data)
        return records_count

    def get_earliest_weight_data(self, max_empty_days: int = 60) -> Optional[datetime]:
        """Get the earliest date for which weight data is available."""
        try:
            current_date = datetime.now()
            empty_days_count = 0
            earliest_timestamp = None

            while empty_days_count < max_empty_days:
                date_str = current_date.strftime("%Y-%m-%d")
                logging.info(f"Fetching data for {date_str}")

                response = self.client.get_body_composition(date_str)
                data_list = response.get("dateWeightList", [])

                if not data_list:
                    empty_days_count += 30
                else:
                    empty_days_count = 0
                    timestamp, _ = self._process_garmin_data(data_list)
                    if earliest_timestamp is None or timestamp < earliest_timestamp:
                        earliest_timestamp = timestamp

                current_date -= timedelta(days=30)

            return (
                datetime.fromtimestamp(earliest_timestamp / 1000)
                if earliest_timestamp
                else None
            )

        except Exception as e:
            logging.error(f"Error in get_earliest_weight_data: {e}")
            return None
