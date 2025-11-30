from pydantic import BaseModel

class SaveMarkdownRequest(BaseModel):
    content: str

class FetchMarkdownResponse(BaseModel):
    doc_id: str
    content: str
