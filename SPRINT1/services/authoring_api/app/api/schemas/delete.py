from pydantic import BaseModel
#from uuid import UUID

class FileDeleteRequest(BaseModel):
    #tenant_id: UUID   # Must match blob path (now consistent with upload schema)
    blob_path: str    # Full path: tenant/{id}/authoring/uploads/{guid}.ext

class FileDeleteResponse(BaseModel):
    success: bool
