import time
import uuid
from psycopg_pool import AsyncConnectionPool

from services.authoring_api.app.utils.azure_client import blob_service_client, CONTAINER_NAME
from services.authoring_api.app.common.observability.audit import AuditService
from services.authoring_api.app.common.observability.error_logging import ErrorLoggingService
from services.authoring_api.app.common.observability.metrics import increment_counter, record_histogram

# ▶ Sensei logging
from common.sensei_common.logging.logger import get_logger, bind_trace
from common.sensei_common.utils.tracing import TraceContext

# Hardcoded tenant (same as your old code)
TENANT_ID = "123e4567-e89b-12d3-a456-426614174099"

# ▶ Service-level logger
logger = get_logger("blob.storage.delete")


async def delete_blob(
    blob_path: str,
    pool: AsyncConnectionPool,
    trace_ctx: TraceContext = None,
    user_id: str = "system",
    tenant_id: str = TENANT_ID
) -> bool:
    """
    Delete blob from Azure Blob Storage (async).
    Same functionality as old code + structured logging + observability.
    """
    timer_start = time.time()
    trace_id = str(uuid.uuid4()) if not trace_ctx else trace_ctx.trace_id

    # Ensure trace context exists
    trace_ctx = trace_ctx or TraceContext(
        trace_id=trace_id,
        span_id=str(uuid.uuid4()),
        parent_span_id=None,
        component="blob",
        stage="storage",
        feature="delete",
    )

    # Security check (same as your old code)
    expected_prefix = f"tenant/{tenant_id}/"
    if not blob_path.startswith(expected_prefix):
        logger.info(
            "blob_delete_invalid_path",
            extra=bind_trace(logger, trace_ctx, {
                "blob_path": blob_path,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "ka_code": "KA-DEL-0400"
            })
        )
        return False

    # Instantiate services (internal only)
    audit_service = AuditService(pool)
    error_service = ErrorLoggingService(pool)

    try:
        logger.info(
            "blob_delete_start",
            extra=bind_trace(logger, trace_ctx, {
                "blob_path": blob_path,
                "tenant_id": tenant_id,
                "user_id": user_id
            })
        )

        blob_client = blob_service_client.get_blob_client(
            container=CONTAINER_NAME,
            blob=blob_path
        )

        # Check existence
        exists = await blob_client.exists()
        if not exists:
            logger.info(
                "blob_delete_not_found",
                extra=bind_trace(logger, trace_ctx, {
                    "blob_path": blob_path,
                    "tenant_id": tenant_id,
                    "user_id": user_id
                })
            )
            return False

        # Async delete
        await blob_client.delete_blob()

        latency_ms = (time.time() - timer_start) * 1000

        logger.info(
            "blob_delete_end",
            extra=bind_trace(logger, trace_ctx, {
                "blob_path": blob_path,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "duration_ms": round(latency_ms, 2)
            })
        )

        # Audit logging
        await audit_service.log_action(
            tenant_id=tenant_id,
            user_id=user_id,
            action="authoring.file.delete",
            object_id=tenant_id,
            payload={
                "blob_path": blob_path,
                "latency_ms": round(latency_ms, 2)
            },
            trace_id=trace_id
        )

        # Metrics
        increment_counter(
            "blob_operations_total",
            labels={
                "operation": "delete",
                "status": "success",
                "tenant_id": tenant_id
            }
        )
        record_histogram(
            "blob_delete_latency_ms",
            latency_ms,
            labels={"tenant_id": tenant_id}
        )

        return True

    except Exception as e:
        latency_ms = (time.time() - timer_start) * 1000

        logger.exception(
            "blob_delete_error",
            extra=bind_trace(logger, trace_ctx, {
                "blob_path": blob_path,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "duration_ms": round(latency_ms, 2),
                "ka_code": "KA-BLOB-0005"
            })
        )

        await error_service.log_error(
            tenant_id=tenant_id,
            doc_id=None,
            task="authoring.file.delete",
            error_code="KA-BLOB-0005",
            reason=f"Blob delete failed: {str(e)}",
            retriable=True,
            trace_id=trace_id
        )

        increment_counter(
            "blob_operations_total",
            labels={
                "operation": "delete",
                "status": "error",
                "tenant_id": tenant_id
            }
        )
        raise
