import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator
from Model.Role import Role

class User(BaseModel):
    id: uuid.UUID
    FirstName: str
    SecondName: str
    Passport: str
    Email: EmailStr
    Confirm_email: bool
    Phone: str
    Confirm_phone: bool
    Hash_password: str
    Cooldown: datetime
    Role: Role
    Agreements_status: bool
