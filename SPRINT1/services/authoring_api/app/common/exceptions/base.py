from typing import Optional
from uuid import UUID
from services.authoring_api.app.common.error_codes import ErrorCodes


class AppException(Exception):
    """Base exception for all application errors"""
    
    def __init__(
        self,
        message: str,
        code: str = ErrorCodes.INTERNAL_ERROR,
        status_code: Optional[int] = None,
        details: Optional[dict] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code or ErrorCodes.get_http_status(code)
        self.details = details or {}
        super().__init__(self.message)
    
    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"
    
    def to_dict(self) -> dict:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details
            }
        }


class DocumentNotFoundException(AppException):
    """Document not found - Used by ALL features"""
    
    def __init__(
        self,
        message: str = "Document not found",
        doc_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None
    ):
        details = {}
        if doc_id:
            details["doc_id"] = str(doc_id)
        if tenant_id:
            details["tenant_id"] = str(tenant_id)
        
        super().__init__(
            message=message,
            code=ErrorCodes.DOC_NOT_FOUND,
            status_code=404,
            details=details
        )


class UnauthorizedException(AppException):
    """Unauthorized access - Used by ALL features"""
    
    def __init__(
        self,
        message: str = "Unauthorized access",
        doc_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None
    ):
        details = {}
        if doc_id:
            details["doc_id"] = str(doc_id)
        if tenant_id:
            details["tenant_id"] = str(tenant_id)
        
        super().__init__(
            message=message,
            code=ErrorCodes.DOC_UNAUTHORIZED,
            status_code=403,
            details=details
        )


class BlobStorageException(AppException):
    """Blob storage errors - Used by ALL features"""
    
    def __init__(
        self,
        message: str = "Blob storage operation failed",
        operation: Optional[str] = None,
        blob_path: Optional[str] = None,
        doc_id: Optional[UUID] = None,
        code: str = ErrorCodes.BLOB_FETCH_FAILED
    ):
        details = {}
        if operation:
            details["operation"] = operation
        if blob_path:
            details["blob_path"] = blob_path
        if doc_id:
            details["doc_id"] = str(doc_id)
        
        super().__init__(
            message=message,
            code=code,
            status_code=500,
            details=details
        )


class DatabaseException(AppException):
    """Database errors - Used by ALL features"""
    
    def __init__(
        self,
        message: str = "Database operation failed",
        operation: Optional[str] = None
    ):
        details = {}
        if operation:
            details["operation"] = operation
        
        super().__init__(
            message=message,
            code=ErrorCodes.DB_QUERY_FAILED,
            status_code=500,
            details=details
        )