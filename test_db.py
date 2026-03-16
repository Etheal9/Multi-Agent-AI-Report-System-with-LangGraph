import pytest
from unittest.mock import patch, MagicMock
from db_manager import get_postgres_saver, fetch_thread_history

def test_fetch_thread_history_empty_on_error():
    """Test that fetch_thread_history gracefully returns empty list on DB error."""
    with patch("db_manager.psycopg.connect") as mock_connect:
        mock_connect.side_effect = Exception("DB Down")
        history = fetch_thread_history()
        assert history == []

def test_get_postgres_saver_context_mgr():
    """Test the context manager initializes the checkpointer correctly when mocked."""
    with patch("db_manager.ConnectionPool") as mock_pool:
        # Mock the context manager behavior of ConnectionPool
        mock_pool_instance = mock_pool.return_value.__enter__.return_value
        
        with patch("db_manager.PostgresSaver") as mock_saver:
            mock_saver_instance = mock_saver.return_value
            
            with get_postgres_saver() as saver:
                assert saver == mock_saver_instance
                mock_saver_instance.setup.assert_called_once()
