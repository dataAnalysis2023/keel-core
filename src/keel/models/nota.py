"""Modelo de nota personal."""

from datetime import date

from pydantic import BaseModel, Field
import uuid


class Nota(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    fecha: str = Field(default_factory=lambda: date.today().isoformat())
    contenido: str
    temas: list[str] = []
