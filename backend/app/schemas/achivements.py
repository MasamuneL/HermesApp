from pydantic import BaseModel, ConfigDict
from uuid import UUID

class AchivementsResponse(BaseModel):
    ach_id : int
    ach_title : str
    ach_desc : str
    ach_points : int
    ach_rank : int
    fecha_objetivo : int 
    status_completed : bool

    model_config = ConfigDict(from_attributes=True)
