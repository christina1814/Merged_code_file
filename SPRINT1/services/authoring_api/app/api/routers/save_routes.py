# app/api/routers/save_routes.py
from fastapi import APIRouter, HTTPException, Depends
import uuid

from services.authoring_api.app.api.schemas.fetch_save import SaveMarkdownRequest
from services.authoring_api.app.services.save_service import save_markdown_content
from services.authoring_api.app.utils.db import get_postgres_client

router = APIRouter(prefix="/api/v1/save", tags=["Save"])


@router.post("/{doc_id}")
async def save_markdown(
    doc_id: str,
    request: SaveMarkdownRequest,
    pool=Depends(get_postgres_client)
):
    """
    Save markdown content to blob storage.

    Path Parameters:
        doc_id: Document UUID

    Request Body:
        content: Markdown content to save

    Returns:
        Success message
    """
    trace_id = str(uuid.uuid4())
    user_id = "system"  # internal only

    try:
        # Query DB for the blob path (storage_path_raw)
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT storage_path_raw FROM authoring_docs WHERE id = %s",
                    (doc_id,)
                )
                row = await cur.fetchone()

        if not row or not row[0]:
            raise HTTPException(status_code=404, detail="Document not found")

        blob_path = row[0]

        # Save content to the existing blob path
        await save_markdown_content(
            blob_path=blob_path,
            content=request.content,
            doc_id=doc_id,
            pool=pool
        )

        return {"success": True, "message": f"Document {doc_id} saved successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save markdown: {str(e)}")
