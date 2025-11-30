from fastapi import APIRouter, HTTPException, Depends
import uuid

from services.authoring_api.app.api.schemas.fetch_save import FetchMarkdownResponse
from services.authoring_api.app.services.fetch_service import fetch_markdown_content
from services.authoring_api.app.utils.db import get_postgres_client

router = APIRouter(prefix="/api/v1/fetch", tags=["Fetch"])


@router.get("/{doc_id}", response_model=FetchMarkdownResponse)
async def fetch_markdown(
    doc_id: str,
    pool=Depends(get_postgres_client)
):
    """
    Fetch markdown content from blob storage.

    Path Parameters:
        doc_id: Document UUID

    Returns:
        FetchMarkdownResponse with doc_id and content
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
            raise HTTPException(status_code=404, detail="Document not found or no raw content available")

        blob_path = row[0]

        # Fetch markdown content
        content = await fetch_markdown_content(
            blob_path=blob_path,
            doc_id=doc_id,
            pool=pool
        )

        return FetchMarkdownResponse(doc_id=doc_id, content=content)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch markdown: {str(e)}")
