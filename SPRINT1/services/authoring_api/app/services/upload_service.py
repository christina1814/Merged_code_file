import time
import uuid
from datetime import datetime, timedelta
from typing import List, Optional
from psycopg_pool import AsyncConnectionPool

from azure.storage.blob import generate_blob_sas, BlobSasPermissions

from services.authoring_api.app.utils.azure_client import blob_service_client, CONTAINER_NAME
from services.authoring_api.app.api.schemas.upload_combined import FileItem, FileUploadResponseItem
from services.authoring_api.app.common.observability.audit import AuditService
from services.authoring_api.app.common.observability.error_logging import ErrorLoggingService
from services.authoring_api.app.common.observability.metrics import increment_counter, record_histogram

# ▶ Sensei logging
from common.sensei_common.logging.logger import get_logger, bind_trace
from common.sensei_common.utils.tracing import TraceContext

# Hardcoded tenant (same as your old code)
TENANT_ID = "123e4567-e89b-12d3-a456-426614174099"

# ▶ Service-level logger: blob.storage.sas_generation
logger = get_logger("blob.storage.sas_generation")


async def generate_sas_urls(
    files: List[FileItem],
    pool: AsyncConnectionPool,
    trace_ctx: Optional[TraceContext] = None,
    user_id: Optional[str] = "system",
    tenant_id: Optional[str] = TENANT_ID
) -> List[FileUploadResponseItem]:
    """
    Generate SAS URLs for file uploads (async).
    Same functionality as old code + structured logging + observability.
    """
    timer_start = time.time()
    trace_id = (trace_ctx.trace_id if trace_ctx else str(uuid.uuid4()))
    # Ensure a trace context exists (for logs)
    trace_ctx = trace_ctx or TraceContext(
        trace_id=trace_id,
        span_id=str(uuid.uuid4()),
        parent_span_id=None,
        component="blob",   # connector component
        stage="storage",
        feature="sas_generation",
    )

    # Instantiate services (internal only)
    audit_service = AuditService(pool)
    error_service = ErrorLoggingService(pool)

    try:
        # ▶ Span start
        logger.info(
            "blob_sas_generation_start",
            extra=bind_trace(logger, trace_ctx, {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "file_count": len(files),
                "files": [f.file for f in files]
            })
        )

        response_items: List[FileUploadResponseItem] = []

        for file_item in files:
            # SAME LOGIC AS YOUR OLD CODE
            file_guid = str(uuid.uuid4())
            file_extension = file_item.file.split(".")[-1] if "." in file_item.file else ""
            blob_name = f"{file_guid}.{file_extension}" if file_extension else file_guid
            blob_path = f"tenant/{tenant_id}/authoring/uploads/{blob_name}"

            # ▶ Per-item start (optional granularity)
            logger.info(
                "blob_sas_item_start",
                extra=bind_trace(logger, trace_ctx, {
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "blob_path": blob_path,
                    "original_filename": file_item.file
                })
            )

            # Generate SAS token (same as old code)
            sas_token = generate_blob_sas(
                account_name=blob_service_client.account_name,
                container_name=CONTAINER_NAME,
                blob_name=blob_path,
                account_key=blob_service_client.credential.account_key,
                permission=BlobSasPermissions(read=True, write=True, create=True),
                expiry=datetime.utcnow() + timedelta(minutes=5)
            )

            # Construct URLs (same as old code)
            blob_url = f"{blob_service_client.url}/{CONTAINER_NAME}/{blob_path}"
            sas_url = f"{blob_url}?{sas_token}"

            response_items.append(FileUploadResponseItem(
                file=file_item.file,
                sas_url=sas_url,
                blob_path=blob_path,
                blob_url=blob_url
            ))

            # ▶ Per-item end (optional granularity)
            logger.info(
                "blob_sas_item_end",
                extra=bind_trace(logger, trace_ctx, {
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "blob_path": blob_path,
                    "blob_url": blob_url
                })
            )

        # Calculate latency (internal)
        latency_ms = (time.time() - timer_start) * 1000

        # ▶ Span end
        logger.info(
            "blob_sas_generation_end",
            extra=bind_trace(logger, trace_ctx, {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "file_count": len(files),
                "duration_ms": round(latency_ms, 2)
            })
        )

        # Audit logging (internal - user doesn't see this)
        await audit_service.log_action(
            tenant_id=tenant_id,
            user_id=user_id,
            action="authoring.file.upload.sas_generated",
            object_id=tenant_id,
            payload={
                "file_count": len(files),
                "files": [f.file for f in files],
                "latency_ms": round(latency_ms, 2)
            },
            trace_id=trace_id
        )

        # Metrics (internal)
        increment_counter(
            "blob_operations_total",
            labels={
                "operation": "sas_generation",
                "status": "success",
                "tenant_id": str(tenant_id)
            },
            value=len(files)
        )

        record_histogram(
            "upload_latency_ms",
            latency_ms,
            labels={"tenant_id": str(tenant_id)}
        )

        return response_items

    except Exception as e:
        # Calculate latency for error case
        latency_ms = (time.time() - timer_start) * 1000

        # ▶ Error log with KA code
        logger.exception(
            "blob_sas_generation_error",
            extra=bind_trace(logger, trace_ctx, {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "file_count": len(files),
                "duration_ms": round(latency_ms, 2),
                "ka_code": "KA-BLOB-0003"
            })
        )

        # Error logging (internal)
        await error_service.log_error(
            tenant_id=tenant_id,
            doc_id=None,
            task="authoring.file.upload.sas_generation",
            error_code="KA-BLOB-0003",
            reason=f"SAS token generation failed: {str(e)}",
            retriable=True,
            trace_id=trace_id
        )

        # Error metrics (internal)
        increment_counter(
            "blob_operations_total",
            labels={
                "operation": "sas_generation",
                "status": "error",
                "tenant_id": str(tenant_id)
            }
        )

        raise
