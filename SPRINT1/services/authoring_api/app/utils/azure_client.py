# app/utils/azure_client.py
import os
from azure.storage.blob.aio import BlobServiceClient  # Changed to async
from dotenv import load_dotenv

load_dotenv()

authoring_api_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
env_path = os.path.join(authoring_api_root, ".env")
load_dotenv(dotenv_path=env_path)

# Azure Blob Storage configuration
AZURE_CONNECTION_STRING = os.getenv("AZURE_CONNECTION_STRING")
CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME")

# Async BlobServiceClient
blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)

# Async Container client
container_client = blob_service_client.get_container_client(CONTAINER_NAME)