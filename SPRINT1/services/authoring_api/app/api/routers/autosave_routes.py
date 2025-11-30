import logging
from fastapi import APIRouter, HTTPException, Header, Depends
from typing import Optional
from uuid import UUID
import uuid

from services.authoring_api.app.services.autosave_service import get_autosave_service
from services.authoring_api.app.api.schemas.autosave import (
    AutosaveRequest,
    AutosaveResponse,
    AutosaveErrorResponse,
    AutosaveErrorDetail
)
from services.authoring_api.app.common.exceptions import (
    DocumentNotFoundException,
    VersionConflictException,
    InvalidStatusException,
    BlobStorageException,
    DatabaseException
)
from services.authoring_api.app.utils.db import get_postgres_client

router = APIRouter(prefix="/api/authoring", tags=["Autosave"])
logger = logging.getLogger("authoring.routes.autosave")


@router.patch("/draft/{doc_id}", response_model=AutosaveResponse)
async def autosave_draft(
    doc_id: str,
    request: AutosaveRequest,
    pool=Depends(get_postgres_client),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    x_trace_id: Optional[str] = Header(None, alias="X-Trace-ID"),
):
    """
    Autosave draft with conflict resolution.
    """
    trace_id = x_trace_id or str(uuid.uuid4())

    try:
        doc_uuid = UUID(doc_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid doc_id format")

    logger.info(
        f"Autosave request received: doc_id={doc_id}, user_id={x_user_id}, "
        f"content_length={len(request.content)}, trace_id={trace_id}"
    )

    try:
        autosave_service = get_autosave_service(pool=pool)

        result = await autosave_service.autosave_draft(
            pool=pool,
            doc_id=doc_uuid,
            request=request,
            user_id=x_user_id,
            trace_id=trace_id
        )

        logger.info(
            f"Autosave successful: doc_id={doc_id}, new_version={result.new_version}, "
            f"status={result.status}"
        )

        return result

    except DocumentNotFoundException as e:
        raise HTTPException(
            status_code=404,
            detail=AutosaveErrorResponse(
                error=AutosaveErrorDetail(code=e.code, message=e.message, details=e.details),
                trace_id=trace_id
            ).dict()
        )

    except InvalidStatusException as e:
        raise HTTPException(
            status_code=400,
            detail=AutosaveErrorResponse(
                error=AutosaveErrorDetail(code=e.code, message=e.message, details=e.details),
                trace_id=trace_id
            ).dict()
        )

    except VersionConflictException as e:
        raise HTTPException(
            status_code=409,
            detail=AutosaveErrorResponse(
                error=AutosaveErrorDetail(code=e.code, message=e.message, details=e.details),
                trace_id=trace_id
            ).dict()
        )

    except (BlobStorageException, DatabaseException) as e:
        raise HTTPException(
            status_code=500,
            detail=AutosaveErrorResponse(
                error=AutosaveErrorDetail(code=e.code, message=e.message, details=e.details),
                trace_id=trace_id
            ).dict()
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=AutosaveErrorResponse(
                error=AutosaveErrorDetail(
                    code="KA-API-0001",
                    message="Internal server error",
                    details={"error": str(e)}
                ),
                trace_id=trace_id
            ).dict()
        )
