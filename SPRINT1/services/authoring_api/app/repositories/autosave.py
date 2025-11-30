"""
Autosave repository.

Uses standard Python logging (no sensei_common dependencies).
"""

import logging
from typing import Optional, Dict, Any, TYPE_CHECKING
from uuid import UUID

# Type checking import (doesn't run at runtime)
if TYPE_CHECKING:
    from psycopg_pool import AsyncConnectionPool

from services.authoring_api.app.common.exceptions import DatabaseException


class AutosaveRepository:
    """Repository for autosave operations (LOGIC UNCHANGED)"""
    
    def __init__(self):
        self.logger = logging.getLogger("authoring.repository.autosave")
    
    async def get_draft_by_id(
        self,
        pool: "AsyncConnectionPool",
        doc_id: UUID,
        tenant_id: Optional[UUID] = None,
        trace_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Fetch draft document (LOGIC UNCHANGED)"""
        
        query = """
            SELECT id, tenant_id, title, version, status, storage_path_raw,
            last_updated, created_at
            FROM authoring_docs
            WHERE id = %s
        """
        
        params = [doc_id]
        if tenant_id:
            query += " AND tenant_id = %s"
            params.append(tenant_id)
        
        try:
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(query, params)
                    row = await cur.fetchone()
                    
                    if row is None:
                        return None
                    
                    columns = [desc[0] for desc in cur.description]
                    return dict(zip(columns, row))
        
        except Exception as e:
            self.logger.error(
                f"Failed to fetch draft: doc_id={doc_id}, error={str(e)}",
                exc_info=True
            )
            raise DatabaseException(
                message=f"Failed to fetch draft: {str(e)}",
                operation="get_draft_by_id"
            )
    
    async def update_draft_with_versioning(
        self,
        pool: "AsyncConnectionPool",
        doc_id: UUID,
        tenant_id: UUID,
        expected_version: int,
        new_storage_path: str,
        trace_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Update with optimistic locking (LOGIC UNCHANGED)"""
        
        query = """
            UPDATE authoring_docs
            SET version = version + 1,
                storage_path_raw = %s,
                last_updated = NOW()
            WHERE id = %s AND tenant_id = %s AND version = %s
            RETURNING id, version, storage_path_raw, last_updated
        """
        
        try:
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        query,
                        (new_storage_path, doc_id, tenant_id, expected_version)
                    )
                    
                    row = await cur.fetchone()
                    if row is None:
                        return None
                    
                    columns = [desc[0] for desc in cur.description]
                    return dict(zip(columns, row))
        
        except Exception as e:
            self.logger.error(
                f"Failed to update draft: doc_id={doc_id}, expected_version={expected_version}, "
                f"error={str(e)}",
                exc_info=True
            )
            raise DatabaseException(
                message=f"Failed to update draft: {str(e)}",
                operation="update_draft_with_versioning"
            )


autosave_repository = AutosaveRepository()


def get_autosave_repository() -> AutosaveRepository:
    """Get singleton repository instance"""
    return autosave_repository