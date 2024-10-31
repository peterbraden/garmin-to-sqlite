import pytest
from datetime import datetime
import os
import json
from unittest.mock import Mock, patch
from garmin_sync import GarminWeightTracker, WeightMeasurement


@pytest.fixture
def mock_garmin_data():
    return {
        "dateWeightList": [
            {
                "date": 1641024000000,  # 2022-01-01
                "weight": 70.5,
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

    assert row[0] == 1641024000000  # timestamp
    assert row[1] == "2022-01-01"  # date
    assert row[2] == 70.5  # weight
    assert row[3] == 22.1  # bmi
    mock_client.get_body_composition.assert_called_with("2022-01-01")


def test_get_earliest_weight_data_custom_max_days(tracker):
    """Test that get_earliest_weight_data respects custom max_empty_days parameter"""
    mock_client = Mock()
    
    # First return empty data, then return some data
    mock_client.get_body_composition.side_effect = [
        {"dateWeightList": []},  # First call - empty
        {"dateWeightList": []},  # Second call - empty
        {"dateWeightList": [     # Third call - has data
            {
                "date": 1640937600000,  # 2021-12-31
                "weight": 71.0,
                "bmi": 22.3,
                "sourceType": "manual",
            }
        ]},
    ]
    tracker.client = mock_client
    tracker.setup_database()

    # Should make 2 attempts (60 days) before giving up
    result = tracker.get_earliest_weight_data(max_empty_days=60)
    assert mock_client.get_body_composition.call_count == 2
    assert result is None

    # Reset mock
    mock_client.reset_mock()
    mock_client.get_body_composition.side_effect = [
        {"dateWeightList": []},  # First call - empty
        {"dateWeightList": []},  # Second call - empty
        {"dateWeightList": []},  # Third call - empty
        {"dateWeightList": []},
    ]

    # Should make 4 attempts (120 days) before giving up
    result = tracker.get_earliest_weight_data(max_empty_days=120)
    assert mock_client.get_body_composition.call_count == 4
    assert result is None


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
            source_type="manual"
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
            source_type="manual"
        )
    ]
    
    earliest_timestamp, count = tracker._process_garmin_data(test_data)
    
    assert earliest_timestamp == 1640937600000  # Should be the earlier date
    assert count == 2
    
    # Verify data was stored correctly
    cursor = tracker._db.cursor()
    cursor.execute("SELECT * FROM weight_measurements ORDER BY timestamp")
    rows = cursor.fetchall()
    
    assert len(rows) == 2
    assert rows[0][0] == 1640937600000  # timestamp of first row
    assert rows[0][1] == "2021-12-31"   # date of first row
    assert rows[0][2] == 71.0           # weight of first row
    assert rows[1][0] == 1641024000000  # timestamp of second row
    assert rows[1][2] == 70.5           # weight of second row
