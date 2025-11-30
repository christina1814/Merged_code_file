class ErrorCodes:
    # Document errors (used by all)
    DOC_NOT_FOUND = "KA-API-0004"
    DOC_UNAUTHORIZED = "KA-API-0403"
    
    # Autosave specific
    VERSION_CONFLICT = "KA-AUTH-0409"
    INVALID_STATUS = "KA-AUTH-0400"
    
    # General API errors
    BAD_REQUEST = "KA-API-0400"
    INTERNAL_ERROR = "KA-API-0001"
    VALIDATION_ERROR = "KA-API-0422"
    
    # Blob storage errors (used by all)
    BLOB_FETCH_FAILED = "KA-BLOB-0001"
    BLOB_SAVE_FAILED = "KA-BLOB-0002"
    BLOB_DELETE_FAILED = "KA-BLOB-0003"
    BLOB_NOT_FOUND = "KA-BLOB-0404"
    
    # Database errors (used by all)
    DB_CONNECTION_FAILED = "KA-DB-0001"
    DB_QUERY_FAILED = "KA-DB-0003"
    DB_TIMEOUT = "KA-DB-0408"
    
    @staticmethod
    def get_http_status(error_code: str) -> int:
        """Extract HTTP status from error code"""
        if error_code and len(error_code) >= 4:
            try:
                status = int(error_code[-4:])
                if 100 <= status <= 599:
                    return status
            except ValueError:
                pass
        return 500