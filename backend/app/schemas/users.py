from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import date


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str] = None
    u_degree: Optional[str] = None
    semester: Optional[int] = None
    universidad: Optional[str] = None
    birth_date: Optional[date] = None
    photo_url: Optional[str] = None
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    u_degree: Optional[str] = None
    semester: Optional[int] = None
    universidad: Optional[str] = None
    birth_date: Optional[date] = None
