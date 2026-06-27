from pydantic import BaseModel, Field


class PromesaProxima(BaseModel):
    persona: str
    descripcion: str
    fecha_limite: str
    dias_restantes: int


class PersonaSinContacto(BaseModel):
    nombre: str
    ultima_interaccion: str
    dias_sin_contacto: int


class DigestRelacional(BaseModel):
    fecha: str
    promesas_proximas: list[PromesaProxima] = Field(default_factory=list)
    personas_sin_contacto: list[PersonaSinContacto] = Field(default_factory=list)
    temas_recurrentes: list[str] = Field(default_factory=list)
    sintesis: str = ""
