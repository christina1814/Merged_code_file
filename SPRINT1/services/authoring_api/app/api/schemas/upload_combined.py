from pydantic import BaseModel
#from uuid import UUID
from typing import List

# -------------------------
# File item
# -------------------------
class FileItem(BaseModel):
    file: str   # UI passes full file name (e.g., "invoice.pdf")


# -------------------------
# Upload request (single & bulk)
# -------------------------
class FileUploadRequest(BaseModel):
    #tenant_id: UUID
    files: List[FileItem]


# -------------------------
# Upload response (single & bulk)
# -------------------------
class FileUploadResponseItem(BaseModel):
    file: str          # return input filename
    sas_url: str
    blob_path: str
    blob_url: str           # full URL without SAS token


class FileUploadResponse(BaseModel):
    items: List[FileUploadResponseItem]