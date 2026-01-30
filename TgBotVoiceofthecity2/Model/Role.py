import uuid
from pydantic import BaseModel

class Role(BaseModel):
    id: uuid.UUID
    name: str
