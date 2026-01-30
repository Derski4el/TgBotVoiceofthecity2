import uuid

from pydantic import BaseModel,FilePath

class LocationZone(BaseModel):
    id: uuid.UUID
    address: str
    img: FilePath
