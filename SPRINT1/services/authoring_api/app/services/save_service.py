# app/services/save_service.py
import time
import uuid
from psycopg_pool import AsyncConnectionPool

from services.authoring_api.app.utils.azure_client import blob_service_client, CONTAINER_NAME
from services.authoring_api.app.common.observability.audit import AuditService
from services.authoring_api.app.common.observability.error_logging import ErrorLoggingService
from services.authoring_api.app.common.observability.metrics import increment_counter, record_histogram


async def save_markdown_content(
    blob_path: str,
    content: str,
    doc_id: str,
    pool: AsyncConnectionPool
) -> None:
    """
    Save markdown content to Azure Blob Storage (async).
    Same functionality as old code + observability.
    """
    timer_start = time.time()
    trace_id = str(uuid.uuid4())  # Internal trace ID
    
    # Instantiate services (internal only)
    audit_service = AuditService(pool)
    error_service = ErrorLoggingService(pool)
    
    try:
        # SAME LOGIC AS YOUR OLD CODE
        blob_client = blob_service_client.get_blob_client(
            container=CONTAINER_NAME,
            blob=blob_path
        )
        
        # Async upload (same as old code)
        await blob_client.upload_blob(
            content.encode("utf-8"),
            overwrite=True
        )
        
        # Calculate latency (internal)
        latency_ms = (time.time() - timer_start) * 1000
        
        # Audit logging (internal - extract tenant from blob_path if needed)
        tenant_id = blob_path.split("/")[1] if "/" in blob_path else "unknown"
        
        await audit_service.log_action(
            tenant_id=tenant_id,
            user_id="system",
            action="authoring.blob.save",
            object_id=doc_id,
            payload={
                "blob_path": blob_path,
                "content_length": len(content),
                "latency_ms": round(latency_ms, 2)
            },
            trace_id=trace_id
        )
        
        # Metrics (internal)
        increment_counter(
            "blob_operations_total",
            labels={
                "operation": "save",
                "status": "success",
                "tenant_id": tenant_id
            }
        )
        
        record_histogram(
            "blob_save_latency_ms",
            latency_ms,
            labels={"tenant_id": tenant_id}
        )
    
    except Exception as e:
        # Calculate latency for error case
        latency_ms = (time.time() - timer_start) * 1000
        tenant_id = blob_path.split("/")[1] if "/" in blob_path else "unknown"
        
        # Error logging (internal)
        await error_service.log_error(
            tenant_id=tenant_id,
            doc_id=doc_id,
            task="authoring.blob.save",
            error_code="KA-BLOB-0004",
            reason=f"Blob save failed: {str(e)}",
            retriable=True,
            trace_id=trace_id
        )
        
        # Error metrics (internal)
        increment_counter(
            "blob_operations_total",
            labels={
                "operation": "save",
                "status": "error",
                "tenant_id": tenant_id
            }
        )
        
        raise