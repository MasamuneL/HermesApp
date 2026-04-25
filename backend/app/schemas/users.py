from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str] = None
    u_degree: Optional[str] = None
    semester: Optional[int] = None
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)
