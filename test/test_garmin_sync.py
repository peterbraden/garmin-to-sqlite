import pytest
from datetime import datetime
import os
import json
from unittest.mock import Mock, patch
from garmin_sync import GarminWeightTracker

@pytest.fixture
def mock_fixture_data():
    return [
        {
            "timestamp": 1641024000000,  # 2022-01-01
            "date": "2022-01-01",
            "weight": 70.5,
            "bmi": 22.1,
            "body_fat": 15.0,
            "body_water": 60.0,
            "bone_mass": 3.2,
            "muscle_mass": 55.3,
            "physique_rating": "lean",
            "visceral_fat": 7.0,
            "metabolic_age": 25,
            "source_type": "manual"
        }
    ]

@pytest.fixture
def tracker():
    # Use temporary paths for testing
    return GarminWeightTracker(
        email="test@example.com",
        password="password123",
        db_path=":memory:",  # Use in-memory SQLite database
        token_file="test_token.json"
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
            'timestamp', 'date', 'weight', 'bmi', 'body_fat', 'body_water',
            'bone_mass', 'muscle_mass', 'physique_rating', 'visceral_fat',
            'metabolic_age', 'source_type', 'created_at', 'source'
        ]
        
    assert columns == expected_columns

def test_get_weight_data_fixture(tracker, mock_fixture_data):
    """Test getting weight data from fixture"""
    start_date = datetime(2022, 1, 1)
    end_date = datetime(2022, 1, 2)
    
    with patch('builtins.open') as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_fixture_data)
        data = tracker.get_weight_data(start_date, end_date)
        
    assert len(data) == 1
    assert data[0]['weight'] == 70.5
    assert data[0]['date'] == '2022-01-01'

def test_fetch_and_store_weight(tracker, mock_fixture_data):
    """Test storing weight data in database"""
    tracker.setup_database()  # Ensure database is set up
    start_date = datetime(2022, 1, 1)
    end_date = datetime(2022, 1, 2)
    
    with patch.object(tracker, 'get_weight_data', return_value=mock_fixture_data):
        tracker.fetch_and_store_weight(start_date, end_date)
    
    # Verify data was stored correctly
    cursor = tracker._db.cursor()
    cursor.execute("SELECT * FROM weight_measurements")
    row = cursor.fetchone()
    
    assert row[0] == 1641024000000  # timestamp
    assert row[1] == '2022-01-01'   # date
    assert row[2] == 70.5           # weight
    assert row[3] == 22.1           # bmi
