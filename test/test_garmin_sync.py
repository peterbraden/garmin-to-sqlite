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
    with tracker.connect_to_garmin() as conn:
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

@patch('garminconnect.Garmin')
def test_connect_to_garmin_new_login(mock_garmin, tracker):
    """Test connecting to Garmin when no token exists"""
    mock_client = Mock()
    mock_garmin.return_value = mock_client
    
    client = tracker.connect_to_garmin()
    
    assert client == mock_client
    mock_client.login.assert_called_once()
    mock_client.garth.dump.assert_called_once_with(tracker.token_file)

@patch('garminconnect.Garmin')
def test_connect_to_garmin_existing_token(mock_garmin, tracker):
    """Test connecting to Garmin with existing valid token"""
    # Create mock token file
    with open(tracker.token_file, 'w') as f:
        json.dump({"token": "test_token"}, f)
    
    mock_client = Mock()
    mock_garmin.return_value = mock_client
    
    client = tracker.connect_to_garmin()
    
    assert client == mock_client
    mock_client.login.assert_called_once_with(tracker.token_file)
    mock_client.get_full_name.assert_called_once()
    
    # Cleanup
    os.remove(tracker.token_file)

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
    start_date = datetime(2022, 1, 1)
    end_date = datetime(2022, 1, 2)
    
    with patch.object(tracker, 'get_weight_data', return_value=mock_fixture_data):
        tracker.fetch_and_store_weight(start_date, end_date)
    
    # Verify data was stored correctly
    with tracker.connect_to_garmin() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM weight_measurements")
        row = cursor.fetchone()
        
        assert row[0] == 1641024000000  # timestamp
        assert row[1] == '2022-01-01'   # date
        assert row[2] == 70.5           # weight
        assert row[3] == 22.1           # bmi

@patch('garminconnect.Garmin')
def test_get_earliest_weight_data(mock_garmin, tracker):
    """Test finding earliest weight data"""
    mock_client = Mock()
    mock_garmin.return_value = mock_client
    
    # Mock response for first chunk with data
    mock_client.get_body_composition.side_effect = [
        {
            'dateWeightList': [
                {'date': 1641024000000}  # 2022-01-01
            ]
        },
        # Next chunks return empty data to simulate end of history
        {'dateWeightList': []},
        {'dateWeightList': []}
    ]
    
    earliest_date = tracker.get_earliest_weight_data(mock_client)
    
    assert earliest_date == datetime(2022, 1, 1)
    assert mock_client.get_body_composition.call_count >= 2
