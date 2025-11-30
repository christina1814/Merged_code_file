from typing import Optional
from uuid import UUID
from psycopg_pool import AsyncConnectionPool
import time

from services.authoring_api.app.api.schemas.autosave import AutosaveRequest, AutosaveResponse
from services.authoring_api.app.repositories.autosave import get_autosave_repository
from services.authoring_api.app.services.fetch_service import fetch_markdown_content
from services.authoring_api.app.services.save_service import save_markdown_content
from services.authoring_api.app.common.observability import AuditService, ErrorLoggingService, metrics
from services.authoring_api.app.common.exceptions import (
    DocumentNotFoundException,
    VersionConflictException,
    InvalidStatusException,
    BlobStorageException
)


class AutosaveService:
    def __init__(self, pool: Optional[AsyncConnectionPool] = None):
        self.repo = get_autosave_repository()
        
        if pool:
            self.audit_service = AuditService(pool)
            self.error_service = ErrorLoggingService(pool)
        else:
            self.audit_service = None
            self.error_service = None
    
    async def autosave_draft(
        self,
        pool: AsyncConnectionPool,
        doc_id: UUID,
        request: AutosaveRequest,
        trace_id: str,
        user_id: Optional[str] = None
    ) -> AutosaveResponse:
        start_time = time.time()
        
        try:
            draft = await self.repo.get_draft_by_id(pool, doc_id, tenant_id=None, trace_id=trace_id)
            
            if not draft:
                if self.error_service:
                    await self.error_service.log_error(
                        tenant_id=str(doc_id),
                        doc_id=doc_id,
                        task="authoring.draft.autosave",
                        error_code="KA-API-0004",
                        reason=f"Document not found: {doc_id}",
                        retriable=False,
                        trace_id=trace_id
                    )
                
                raise DocumentNotFoundException(
                    message="Draft document not found",
                    doc_id=doc_id
                )
            
            tenant_id = draft['tenant_id']
            current_version = draft['version']
            storage_path = draft['storage_path_raw']
            status = draft.get('status', 'draft')
            
            if status != 'draft':
                raise InvalidStatusException(
                    message=f"Cannot autosave {status} documents",
                    doc_id=doc_id,
                    current_status=status,
                    expected_status='draft'
                )
            
            try:
                # ✅ Updated call: only blob_path, doc_id, pool
                current_content = await fetch_markdown_content(
                    blob_path=storage_path,
                    doc_id=str(doc_id),
                    pool=pool
                )
            except Exception as e:
                raise BlobStorageException(
                    message=f"Failed to fetch content: {str(e)}",
                    operation="fetch",
                    doc_id=doc_id
                )
            
            new_content = request.content
            
            if current_content == new_content:
                latency_ms = (time.time() - start_time) * 1000
                metrics.record_histogram(
                    "autosave_latency_ms",
                    latency_ms,
                    labels={"tenant_id": str(tenant_id), "status": "unchanged"}
                )
                
                return AutosaveResponse(
                    doc_id=doc_id,
                    new_version=current_version,
                    status="unchanged",
                    last_updated=draft['last_updated'],
                    trace_id=trace_id
                )
            
            try:
                # ✅ Updated call: only blob_path, content, doc_id, pool
                await save_markdown_content(
                    blob_path=storage_path,
                    content=new_content,
                    doc_id=str(doc_id),
                    pool=pool
                )
            except Exception as e:
                raise BlobStorageException(
                    message=f"Failed to save content: {str(e)}",
                    operation="save",
                    doc_id=doc_id
                )
            
            updated_draft = await self.repo.update_draft_with_versioning(
                pool=pool,
                doc_id=doc_id,
                tenant_id=tenant_id,
                expected_version=current_version,
                new_storage_path=storage_path,
                trace_id=trace_id
            )
            
            if not updated_draft:
                if self.error_service:
                    await self.error_service.log_error(
                        tenant_id=tenant_id,
                        doc_id=doc_id,
                        task="authoring.draft.autosave",
                        error_code="KA-AUTH-0409",
                        reason=f"Version conflict: server={current_version + 1}, client={current_version}",
                        retriable=True,
                        trace_id=trace_id
                    )
                
                if self.audit_service:
                    await self.audit_service.log_action(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        action="authoring.draft.conflict",
                        object_id=doc_id,
                        payload={
                            "server_version": current_version + 1,
                            "client_version": current_version,
                            "action_type": "version_conflict"
                        },
                        trace_id=trace_id
                    )
                
                metrics.increment_counter("conflict_events_total", labels={"tenant_id": str(tenant_id)})
                
                raise VersionConflictException(
                    message="Another user edited this document",
                    doc_id=doc_id,
                    server_version=current_version + 1,
                    client_version=current_version
                )
            
            new_version = updated_draft['version']
            last_updated = updated_draft['last_updated']
            
            if self.audit_service:
                await self.audit_service.log_action(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    action="authoring.draft.autosave",
                    object_id=doc_id,
                    payload={
                        "old_version": current_version,
                        "new_version": new_version,
                        "action_type": "autosave"
                    },
                    trace_id=trace_id
                )
            
            latency_ms = (time.time() - start_time) * 1000
            metrics.increment_counter("autosave_success_total", labels={"tenant_id": str(tenant_id), "status": "draft"})
            metrics.record_histogram("autosave_latency_ms", latency_ms, labels={"tenant_id": str(tenant_id), "status": "success"})
            
            return AutosaveResponse(
                doc_id=doc_id,
                new_version=new_version,
                status="saved",
                last_updated=last_updated,
                trace_id=trace_id
            )
        
        except (DocumentNotFoundException, InvalidStatusException, VersionConflictException, BlobStorageException):
            if 'tenant_id' in locals():
                metrics.increment_counter("autosave_failure_total", labels={"tenant_id": str(tenant_id), "error_code": "known"})
            raise
        
        except Exception as e:
            if 'tenant_id' in locals() and self.error_service:
                await self.error_service.log_error(
                    tenant_id=tenant_id,
                    doc_id=doc_id,
                    task="authoring.draft.autosave",
                    error_code="KA-API-0001",
                    reason=f"Unexpected error: {str(e)}",
                    retriable=False,
                    trace_id=trace_id
                )
            
            if 'tenant_id' in locals():
                metrics.increment_counter("autosave_failure_total", labels={"tenant_id": str(tenant_id), "error_code": "unknown"})
            
            raise


_autosave_service: Optional[AutosaveService] = None


def get_autosave_service(pool: Optional[AsyncConnectionPool] = None) -> AutosaveService:
    global _autosave_service
    
    if _autosave_service is None or pool:
        _autosave_service = AutosaveService(pool=pool)
    
    return _autosave_service
