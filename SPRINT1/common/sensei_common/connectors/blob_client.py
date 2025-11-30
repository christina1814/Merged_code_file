"""
Azure Blob / ADLS connector for Sensei 2.0.

Responsibilities:
- Upload, download, existence checks
- Versioned paths (raw/refined/published)
- Basic retry and logging
"""

from __future__ import annotations

import asyncio
from typing import Optional

from azure.storage.blob.aio import BlobServiceClient

from common.sensei_common.logging.logger import get_logger


class BlobClient:
    """
    Async Azure Blob Storage client.
    """

    def __init__(
        self,
        conn_str: str,
        container_name: str,
        component: str = "common",
        max_retries: int = 3,
    ) -> None:
        """
        Initialize the Blob client.

        Parameters
        ----------
        conn_str : str
            Azure Storage connection string.
        container_name : str
            Name of the container to use.
        component : str
            Component label ("vendor", "authoring", "common").
        max_retries : int
            Max number of retries per operation.
        """
        self._service = BlobServiceClient.from_connection_string(conn_str)
        self._container_name = container_name
        self._component = component
        self._max_retries = max_retries

    async def _with_retry(self, fn, trace_id: Optional[str] = None):
        logger = get_logger(self._component, "blob", "adls", trace_id)
        delay = 0.2
        for attempt in range(1, self._max_retries + 1):
            try:
                return await fn()
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Blob operation failed on attempt %d: %s", attempt, exc
                )
                if attempt == self._max_retries:
                    logger.error(
                        "Blob operation failed permanently", ka_code="KA-BLOB-0001"
                    )
                    raise
                await asyncio.sleep(delay)
                delay *= 2

    async def upload(
        self,
        blob_path: str,
        data: bytes,
        trace_id: Optional[str] = None,
        content_type: str = "text/plain",
    ) -> None:
        """
        Upload a blob to the container.

        Parameters
        ----------
        blob_path : str
            Path/key within the container.
        data : bytes
            Data to upload.
        content_type : str
            MIME content type.
        """
        container = self._service.get_container_client(self._container_name)

        async def _inner():
            blob = container.get_blob_client(blob_path)
            await blob.upload_blob(data, overwrite=True, content_type=content_type)

        await self._with_retry(_inner, trace_id=trace_id)

    async def download(self, blob_path: str, trace_id: Optional[str] = None) -> bytes:
        """
        Download a blob.

        Returns
        -------
        bytes
            Blob content.
        """
        container = self._service.get_container_client(self._container_name)

        async def _inner():
            blob = container.get_blob_client(blob_path)
            stream = await blob.download_blob()
            return await stream.readall()

        return await self._with_retry(_inner, trace_id=trace_id)

    async def exists(self, blob_path: str, trace_id: Optional[str] = None) -> bool:
        """
        Check if a blob exists.
        """
        container = self._service.get_container_client(self._container_name)

        async def _inner():
            blob = container.get_blob_client(blob_path)
            return await blob.exists()

        return await self._with_retry(_inner, trace_id=trace_id)
