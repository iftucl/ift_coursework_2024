import pytest
from unittest.mock import patch, MagicMock
from pymongo.errors import ConnectionFailure
from fastapi import HTTPException
from team_adansonia.coursework_two.fast_api.db import get_db


class TestDb:
    """Test database connection functionality"""
    
    @patch("team_adansonia.coursework_two.fast_api.db.MongoClient")
    def test_get_db_success(self, mock_client):
        """Test successful database connection"""
        # Setup mock
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        mock_instance.server_info.return_value = {"ok": 1}
        mock_instance.__getitem__.return_value = "test_database"
        
        # Call function
        result = get_db()
        
        # Verify results
        assert result == "test_database"
        mock_client.assert_called_once()
        mock_instance.server_info.assert_called_once()
    
    @patch("team_adansonia.coursework_two.fast_api.db.MongoClient")
    def test_get_db_connection_failure(self, mock_client):
        """Test exception thrown on connection failure"""
        # Setup mock to simulate connection failure
        mock_client.side_effect = ConnectionFailure("Connection error")
        
        # Verify appropriate exception is thrown
        with pytest.raises(HTTPException) as exc_info:
            get_db()
        
        # Verify exception content
        assert exc_info.value.status_code == 500
        assert "Database connection failed" in exc_info.value.detail
    
    @patch("team_adansonia.coursework_two.fast_api.db.MongoClient")
    def test_get_db_other_error(self, mock_client):
        """Test other exception cases"""
        # Setup mock to simulate other exceptions
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        mock_instance.server_info.side_effect = Exception("Unknown error")
        
        # Verify appropriate exception is thrown
        with pytest.raises(HTTPException) as exc_info:
            get_db()
        
        # Verify exception content
        assert exc_info.value.status_code == 500
        assert "Internal server error" in exc_info.value.detail 