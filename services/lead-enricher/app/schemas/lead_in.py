from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from uuid import UUID


class LeadIn(BaseModel):
    request_id: Optional[UUID] = None
    name: str = Field(min_length=1, max_length=256)
    phone: str = Field(min_length=5, max_length=64)
    email: EmailStr
    website: Optional[str] = None
    comment: Optional[str] = None
    utm_source: Optional[str] = None
