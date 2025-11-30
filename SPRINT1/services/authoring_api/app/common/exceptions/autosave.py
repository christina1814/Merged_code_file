from typing import Optional
from uuid import UUID
from services.authoring_api.app.common.exceptions.base import AppException
from services.authoring_api.app.common.error_codes import ErrorCodes


class VersionConflictException(AppException):
    """Version conflict during autosave"""
    
    def __init__(
        self,
        message: str = "Version conflict detected",
        doc_id: Optional[UUID] = None,
        server_version: Optional[int] = None,
        client_version: Optional[int] = None
    ):
        details = {}
        if doc_id:
            details["doc_id"] = str(doc_id)
        if server_version is not None:
            details["server_version"] = server_version
        if client_version is not None:
            details["client_version"] = client_version
        
        super().__init__(
            message=message,
            code=ErrorCodes.VERSION_CONFLICT,
            status_code=409,
            details=details
        )


class InvalidStatusException(AppException):
    """Invalid document status for operation"""
    
    def __init__(
        self,
        message: str = "Invalid document status",
        doc_id: Optional[UUID] = None,
        current_status: Optional[str] = None,
        expected_status: Optional[str] = None
    ):
        details = {}
        if doc_id:
            details["doc_id"] = str(doc_id)
        if current_status:
            details["current_status"] = current_status
        if expected_status:
            details["expected_status"] = expected_status
        
        super().__init__(
            message=message,
            code=ErrorCodes.INVALID_STATUS,
            status_code=400,
            details=details
        )