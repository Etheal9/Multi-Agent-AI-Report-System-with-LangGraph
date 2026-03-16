import pytest
from unittest.mock import patch, MagicMock
from db_manager import get_postgres_saver, fetch_thread_history
from langgraph.checkpoint.memory import MemorySaver

def test_postgres_fallback_to_memory():
    """
    Test that if postgres connection fails, get_postgres_saver gracefully yields MemorySaver.
    """
    # Simply let it fail naturally to connect, it will timeout and yield MemorySaver
    with get_postgres_saver() as checkpointer:
        assert isinstance(checkpointer, MemorySaver)

def test_fetch_thread_history_fallback():
    """
    Test that fetch_thread_history returns [] on database failure.
    """
    # Simply let it fail naturally
    history = fetch_thread_history()
    assert history == []
