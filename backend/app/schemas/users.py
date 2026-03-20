from pydantic import BaseModel, ConfigDict
from uuid import UUID

class UserResponse(BaseModel):
    usr_id : UUID
    name : str
    carrera : str
    u_degree : int
    email : str

    model_config = ConfigDict(from_attributes=True)