from typing import Optional, Dict, Any
from uuid import UUID
from psycopg_pool import AsyncConnectionPool
import json


class AuditService:
    """Generic audit logging service for all features"""
    
    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool
    
    async def log_action(
        self,
        tenant_id: UUID | str,
        user_id: Optional[str],
        action: str,
        object_id: UUID | str,
        payload: Dict[str, Any],
        trace_id: str
    ) -> bool:
        """
        Generic method to log any action
        
        Examples:
            action="authoring.draft.autosave"
            action="authoring.file.upload"
            action="authoring.file.delete"
            action="authoring.document.create"
        """
        query = """
            INSERT INTO audit (
                tenant_id, user_id, action, object_id, payload, created_at
            ) VALUES (%s, %s, %s, %s, %s, NOW())
            RETURNING id;
        """
        
        try:
            tenant_id_str = str(tenant_id)
            object_id_str = str(object_id)
            payload_json = json.dumps(payload)
            
            async with self.pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        query,
                        (tenant_id_str, user_id, action, object_id_str, payload_json)
                    )
                    result = await cur.fetchone()
                    
                    if result:
                        print(f"[AUDIT] trace_id={trace_id} audit_id={result[0]} action={action}")
                        return True
                    return False
        
        except Exception as e:
            print(f"[AUDIT ERROR] trace_id={trace_id} {str(e)}")
            return False