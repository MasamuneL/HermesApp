from pydantic import BaseModel, ConfigDict
from uuid import UUID

class RankingResponse(BaseModel):
    usr_id : UUID
    nombre : str
    carrera : str
    semestre : int 
    correo : str

    model_config = ConfigDict(from_attributes=True)