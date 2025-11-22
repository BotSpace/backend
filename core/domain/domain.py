from pydantic import BaseModel
from typing import Any


class ResponseSchema(BaseModel):
    status: bool = True
    data: Any
