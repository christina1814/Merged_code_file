from fastapi import APIRouter, HTTPException, Depends
import uuid

from services.authoring_api.app.api.schemas.upload_combined import (
    FileUploadRequest,
    FileUploadResponse
)
from services.authoring_api.app.services.upload_service import generate_sas_urls
from services.authoring_api.app.utils.db import get_postgres_client

# ▶ Add Sensei logging imports
from common.sensei_common.logging.logger import get_logger, bind_trace
from common.sensei_common.utils.tracing import TraceContext

router = APIRouter(prefix="/api/v1/uploads", tags=["Upload"])

# ▶ Route-level logger: component.stage.feature → authoring.api.upload_sign
logger = get_logger("authoring.api.upload_sign")


@router.post("/sign", response_model=FileUploadResponse)
async def sign_upload(
    request: FileUploadRequest,
    pool=Depends(get_postgres_client)
):
    """
    Generate SAS URLs for file uploads.

    Request Body:
        files: List of FileItem with file names

    Returns:
        FileUploadResponse with SAS URLs for each file
    """
    # Internal observability values (not exposed in API contract)
    trace_id = str(uuid.uuid4())
    tenant_id = "123e4567-e89b-12d3-a456-426614174099"  # hardcoded for upload/delete
    user_id = "system"  # internal only

    # ▶ Build trace context for consistent structured logs
    trace_ctx = TraceContext(
        trace_id=trace_id,
        span_id=str(uuid.uuid4()),
        parent_span_id=None,
        component="authoring",
        stage="api",
        feature="upload_sign",
    )

    # Validate request
    if not request.files:
        logger.info(
            "upload_sign_request_invalid",
            extra=bind_trace(logger, trace_ctx, {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "file_count": 0,
                "ka_code": "KA-UPL-0400"
            })
        )
        raise HTTPException(status_code=400, detail="No files provided")

    try:
        # ▶ Start log
        logger.info(
            "upload_sign_request_start",
            extra=bind_trace(logger, trace_ctx, {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "file_count": len(request.files),
                "files": [f.file for f in request.files]
            })
        )

        # Generate SAS URLs (service handles observability internally)
        response_items = await generate_sas_urls(
            files=request.files,
            pool=pool,
            trace_ctx=trace_ctx,   # ▶ propagate context
            user_id=user_id,       # ▶ propagate user_id
            tenant_id=tenant_id    # ▶ propagate tenant_id
        )

        # ▶ Success log
        logger.info(
            "upload_sign_request_success",
            extra=bind_trace(logger, trace_ctx, {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "file_count": len(response_items)
            })
        )

        return FileUploadResponse(items=response_items)

    except Exception as e:
        # ▶ Error log
        logger.exception(
            "upload_sign_request_error",
            extra=bind_trace(logger, trace_ctx, {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "file_count": len(request.files),
                "ka_code": "KA-UPL-0001"
            })
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate SAS URLs: {str(e)}"
        )
