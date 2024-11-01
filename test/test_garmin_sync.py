import pytest
from datetime import datetime
import os
import json
from unittest.mock import Mock, patch
from garmin_sync import GarminWeightTracker, WeightMeasurement
from datetime import timedelta

@pytest.fixture
def mock_garmin_data():
    return {
        "dateWeightList": [
            {
                "date": 1641024000000,  # 2022-01-01
                "weight": 70500,
                "bmi": 22.1,
                "bodyFat": 15.0,
                "bodyWater": 60.0,
                "boneMass": 3.2,
                "muscleMass": 55.3,
                "physiqueRating": "lean",
                "visceralFat": 7.0,
                "metabolicAge": 25,
                "sourceType": "manual",
            }
        ]
    }


@pytest.fixture
def tracker():
    # Use temporary paths for testing
    return GarminWeightTracker(
        email="test@example.com",
        password="password123",
        db_path=":memory:",  # Use in-memory SQLite database
        token_file="test_token.json",
    )


def test_setup_database(tracker):
    """Test that database setup creates the correct table structure"""
    tracker.setup_database()
    conn = tracker._db
    cursor = conn.cursor()
    # Check if table exists and has correct columns
    cursor.execute("SELECT * FROM weight_measurements")
    columns = [description[0] for description in cursor.description]

    expected_columns = [
        "timestamp",
        "date",
        "weight",
        "bmi",
        "body_fat",
        "body_water",
        "bone_mass",
        "muscle_mass",
        "physique_rating",
        "visceral_fat",
        "metabolic_age",
        "source_type",
        "created_at",
        "source",
    ]

    assert columns == expected_columns


def test_get_weight_data_fixture(tracker, mock_garmin_data):
    """Test getting weight data from Garmin API"""
    start_date = datetime(2022, 1, 1)
    end_date = datetime(2022, 1, 1)

    # Mock the Garmin client
    mock_client = Mock()
    mock_client.get_body_composition.return_value = mock_garmin_data
    tracker.client = mock_client

    data = tracker.get_weight_data(start_date, end_date)

    assert len(data) == 1
    assert data[0]["weight"] == 70.5
    assert data[0]["date"] == "2022-01-01"
    mock_client.get_body_composition.assert_called_with("2022-01-01")


def test_fetch_and_store_weight(tracker, mock_garmin_data):
    """Test storing weight data in database"""
    tracker.setup_database()  # Ensure database is set up
    start_date = datetime(2022, 1, 1)
    end_date = datetime(2022, 1, 1)

    # Mock the Garmin client
    mock_client = Mock()
    mock_client.get_body_composition.return_value = mock_garmin_data
    tracker.client = mock_client

    records_stored = tracker.fetch_and_store_weight(start_date, end_date)

    assert records_stored == 1  # Should have stored one record

    # Verify data was stored correctly
    cursor = tracker._db.cursor()
    cursor.execute("SELECT * FROM weight_measurements")
    row = cursor.fetchone()

    assert row[0] == 1641024000  # timestamp
    assert row[1] == "2022-01-01"  # date
    assert row[2] == 70.5  # weight
    assert row[3] == 22.1  # bmi
    mock_client.get_body_composition.assert_called_with("2022-01-01")



def test_process_garmin_data(tracker):
    """Test the _process_garmin_data helper method"""
    tracker.setup_database()  # Ensure database is set up

    test_data = [
        WeightMeasurement(
            timestamp=1641024000000,  # 2022-01-01
            date="2022-01-01",
            weight=70.5,
            bmi=22.1,
            body_fat=15.0,
            body_water=60.0,
            bone_mass=3.2,
            muscle_mass=55.3,
            physique_rating="lean",
            visceral_fat=7.0,
            metabolic_age=25,
            source_type="manual",
        ),
        WeightMeasurement(
            timestamp=1640937600000,  # 2021-12-31
            date="2021-12-31",
            weight=71.0,
            bmi=22.3,
            body_fat=15.2,
            body_water=None,
            bone_mass=None,
            muscle_mass=None,
            physique_rating=None,
            visceral_fat=None,
            metabolic_age=None,
            source_type="manual",
        ),
    ]

    count = tracker._process_garmin_data(test_data)
    assert count == 2
    # Verify data was stored correctly
    cursor = tracker._db.cursor()
    cursor.execute("SELECT * FROM weight_measurements ORDER BY timestamp")
    rows = cursor.fetchall()

    assert len(rows) == 2
    assert rows[0][0] == 1640937600000  # timestamp of first row
    assert rows[0][1] == "2021-12-31"  # date of first row
    assert rows[0][2] == 71.0  # weight of first row
    assert rows[1][0] == 1641024000000  # timestamp of second row
    assert rows[1][2] == 70.5  # weight of second row

def test_get_earliest_weight_data(tracker, mock_garmin_data):
    """Test getting earliest weight data with pagination"""
    # Mock the Garmin client
    mock_client = Mock()
    
    # Create mock data for different date ranges
    data_2022_01_01 = {
        "dateWeightList": [{
            "date": 1641024000000,  # 2022-01-01
            "weight": 70500,
            "sourceType": "manual",
        }]
    }
    
    data_2021_12_01 = {
        "dateWeightList": [{
            "date": 1638316800000,  # 2021-12-01
            "weight": 71000,
            "sourceType": "manual",
        }]
    }
    
    data_empty = {"dateWeightList": []}
    
    # Mock get_body_composition to return different data based on the date
    def mock_get_body_composition(date):
        if date >= "2022-01-01":
            return data_2022_01_01
        elif date >= "2021-12-01":
            return data_2021_12_01
        return data_empty
    
    mock_client.get_body_composition.side_effect = mock_get_body_composition
    tracker.client = mock_client

    # Test with a 30-day chunk size starting from 2022-01-01
    start_date = datetime(2022, 1, 1)
    earliest_date = tracker.get_earliest_weight_data(
        chunk_size=30,
        start_date=start_date
    )

    # The earliest date should be exactly 2021-12-01 - 30 days
    assert earliest_date is not None
    assert earliest_date == datetime(2021, 11, 2)

def test_get_earliest_weight_data_no_data(tracker):
    """Test getting earliest weight data when no data is available"""
    mock_client = Mock()
    mock_client.get_body_composition.return_value = {"dateWeightList": []}
    tracker.client = mock_client

    start_date = datetime(2022, 1, 1)
    earliest_date = tracker.get_earliest_weight_data(
        chunk_size=30,
        start_date=start_date
    )

    assert earliest_date is None
