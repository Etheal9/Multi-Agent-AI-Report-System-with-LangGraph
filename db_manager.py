import os
from contextlib import contextmanager

DB_URI = os.getenv("DATABASE_URL", "postgresql://ai_user:ai_password@localhost:5432/multi_agent_reports")

@contextmanager
def get_postgres_saver():
    """
    Context manager that yields a connected PostgresSaver instance.
    If Postgres is unavailable, gracefully falls back to MemorySaver so the app never crashes.
    """
    try:
        from psycopg_pool import ConnectionPool
        from langgraph.checkpoint.postgres import PostgresSaver
        import psycopg
        
        # Test connection quickly (2s timeout) to avoid hanging the UI
        with psycopg.connect(DB_URI, connect_timeout=2) as conn:
            pass
            
        with ConnectionPool(
            conninfo=DB_URI,
            max_size=20,
            kwargs={
                "autocommit": True,
                "prepare_threshold": 0,
            },
        ) as pool:
            checkpointer = PostgresSaver(pool)
            checkpointer.setup()
            yield checkpointer
            return
            
    except Exception as e:
        print(f"⚠️ PostgreSQL unavailable ({e}). Falling back to MemorySaver.")
        from langgraph.checkpoint.memory import MemorySaver
        yield MemorySaver()

def fetch_thread_history():
    """
    Query the postgres table explicitly to retrieve past thread IDs.
    """
    try:
        import psycopg
        with psycopg.connect(DB_URI, connect_timeout=2) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT DISTINCT thread_id FROM checkpoints ORDER BY thread_id DESC LIMIT 50;")
                return [row[0] for row in cur.fetchall()]
    except Exception as e:
        print(f"⚠️ Could not fetch thread history (Database offline)")
        return []
