# app/utils/db.py
import os
from dotenv import load_dotenv

# Load from current directory first
load_dotenv()

# Try to find .env in authoring_api root
current_dir = os.path.dirname(__file__)  # utils/
app_dir = os.path.dirname(current_dir)   # app/
authoring_api_root = os.path.dirname(app_dir)  # authoring_api/
env_path = os.path.join(authoring_api_root, ".env")

# Load again from specific path
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)
    print(f"[DB] ✅ Loaded .env from: {env_path}")
else:
    print(f"[DB] ⚠️ .env file not found at: {env_path}")

DATABASE_URL = os.getenv("DATABASE_URL")

# Validate DATABASE_URL
if not DATABASE_URL:
    raise ValueError(
        f"DATABASE_URL environment variable is not set. "
        f"Checked .env file at: {env_path}"
    )

# ========================================
# PSYCOPG ASYNC POOL (Used by ALL services)
# ========================================
try:
    from psycopg_pool import AsyncConnectionPool
    PSYCOPG_AVAILABLE = True
except ImportError:
    PSYCOPG_AVAILABLE = False
    AsyncConnectionPool = None
    print("[WARN] psycopg not installed")


_db_pool = None


async def init_db():
    """Initialize async database pool"""
    global _db_pool
    
    if not PSYCOPG_AVAILABLE:
        print("[WARN] psycopg not available - skipping async pool")
        return
    
    if not DATABASE_URL:
        print("[WARN] DATABASE_URL not set")
        return
    
    print("[DB] Initializing async pool...")
    
    try:
        _db_pool = AsyncConnectionPool(
            conninfo=DATABASE_URL,
            min_size=1,
            max_size=10,
            timeout=30,
        )
        
        await _db_pool.open()
        print("[DB] ✅ Async pool initialized")
    
    except Exception as e:
        print(f"[DB] ❌ Failed to initialize async pool: {e}")
        raise


async def close_db():
    """Close async database pool"""
    global _db_pool
    
    if _db_pool is not None:
        print("[DB] Closing async pool...")
        try:
            await _db_pool.close()
            print("[DB] ✅ Async pool closed")
        except Exception as e:
            print(f"[DB] ⚠️ Error closing pool: {e}")
        finally:
            _db_pool = None


def get_postgres_client():
    """
    Get async pool for dependency injection.
    Used by ALL services for observability and autosave.
    """
    if _db_pool is None:
        raise RuntimeError("Database pool not initialized - call init_db() first")
    return _db_pool


async def health_check() -> bool:
    """Check if async database is healthy"""
    try:
        if _db_pool is None:
            return False
        
        async with _db_pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
                result = await cur.fetchone()
                return result is not None and result[0] == 1
    
    except Exception as e:
        print(f"[DB] Health check failed: {e}")
        return False