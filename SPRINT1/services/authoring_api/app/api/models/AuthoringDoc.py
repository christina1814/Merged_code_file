from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class AuthoringDoc(Base):
    __tablename__ = "authoring_docs"
    id = Column(PG_UUID(as_uuid=True), primary_key=True)
    storage_path_raw = Column(String)
