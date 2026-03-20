from pydantic import BaseModel, ConfigDict
from uuid import UUID

class RankingResponse(BaseModel):
    usr_id : UUID
    nombre : str
    puntos : int
    nivel : int # Es la division del total de los puntos entre 'x' cantidad
    racha_diaria : int # Solo con abrir la app no por realizar tareas

    model_config = ConfigDict(from_attributes=True)