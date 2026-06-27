from pydantic import BaseModel, Field


class SugerenciasPerfil(BaseModel):
    frases_nuevas: list[str] = Field(default_factory=list)
    vocabulario_nuevo: list[str] = Field(default_factory=list)
    valores_detectados: list[str] = Field(default_factory=list)
    temas_recurrentes: list[str] = Field(default_factory=list)
    resumen: str = ""
