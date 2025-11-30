from fastapi import APIRouter, HTTPException, Depends
import uuid

from services.authoring_api.app.api.schemas.delete import (
    FileDeleteRequest,
    FileDeleteResponse
)
from services.authoring_api.app.services.delete_service import delete_blob
from services.authoring_api.app.utils.db import get_postgres_client

# ▶ Sensei logging
from common.sensei_common.logging.logger import get_logger, bind_trace
from common.sensei_common.utils.tracing import TraceContext

router = APIRouter(prefix="/api/v1/delete", tags=["Delete"])

# ▶ Route-level logger
logger = get_logger("authoring.api.delete")


@router.delete("/", response_model=FileDeleteResponse)
async def delete_file(
    request: FileDeleteRequest,
    pool=Depends(get_postgres_client)
):
    """
    Delete blob from storage.
    """
    trace_id = str(uuid.uuid4())
    tenant_id = "123e4567-e89b-12d3-a456-426614174099"
    user_id = "system"

    trace_ctx = TraceContext(
        trace_id=trace_id,
        span_id=str(uuid.uuid4()),
        parent_span_id=None,
        component="authoring",
        stage="api",
        feature="delete",
    )

    try:
        logger.info(
            "delete_request_start",
            extra=bind_trace(logger, trace_ctx, {
                "blob_path": request.blob_path,
                "tenant_id": tenant_id,
                "user_id": user_id
            })
        )

        success = await delete_blob(
            blob_path=request.blob_path,
            pool=pool,
            trace_ctx=trace_ctx,
            user_id=user_id,
            tenant_id=tenant_id
        )

        logger.info(
            "delete_request_success",
            extra=bind_trace(logger, trace_ctx, {
                "blob_path": request.blob_path,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "success": success
            })
        )

        return FileDeleteResponse(success=success)

    except Exception as e:
        logger.exception(
            "delete_request_error",
            extra=bind_trace(logger, trace_ctx, {
                "blob_path": request.blob_path,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "ka_code": "KA-DEL-0001"
            })
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete blob: {str(e)}"
        )
