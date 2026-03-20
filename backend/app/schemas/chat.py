from pydantic import BaseModel, ConfigDict
from uuid import UUID

class ChatResponse(BaseModel):
    sol_id : int
    staus : bool
    message : str
    embeddings : str | None = None

    