from typing import Optional
from uuid import UUID
from psycopg_pool import AsyncConnectionPool


class ErrorLoggingService:
    """Generic error logging service for all features"""
    
    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool
    
    async def log_error(
        self,
        tenant_id: UUID | str,
        doc_id: Optional[UUID | str],
        task: str,
        error_code: str,
        reason: str,
        retriable: bool,
        trace_id: str
    ) -> bool:
        """
        Generic method to log any error
        
        Examples:
            task="authoring.draft.autosave"
            task="authoring.file.upload"
            task="authoring.blob.fetch"
        """
        query = """
            INSERT INTO errors (
                tenant_id, doc_id, task, code, reason, retriable,
                first_seen, last_seen
            ) VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING id;
        """
        
        try:
            tenant_id_str = str(tenant_id)
            doc_id_str = str(doc_id) if doc_id else None
            
            async with self.pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        query,
                        (tenant_id_str, doc_id_str, task, error_code, reason, retriable)
                    )
                    result = await cur.fetchone()
                    
                    if result:
                        print(f"[ERROR_LOG] trace_id={trace_id} error_id={result[0]} code={error_code}")
                        return True
                    return False
        
        except Exception as e:
            print(f"[ERROR_LOG ERROR] trace_id={trace_id} {str(e)}")
            return False