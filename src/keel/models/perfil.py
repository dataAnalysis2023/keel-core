"""Módulo 1 — Perfil del Yo."""

from pydantic import BaseModel, Field


class VozUsuario(BaseModel):
    tono: str = ""
    registro: str = "informal"  # formal | informal | técnico
    vocabulario_frecuente: list[str] = Field(default_factory=list)
    frases_caracteristicas: list[str] = Field(default_factory=list)


class CoherenciaRegistro(BaseModel):
    fecha: str  # YYYY-MM-DD
    tema: str
    posicion: str


class PerfilUsuario(BaseModel):
    nombre: str
    voz: VozUsuario = Field(default_factory=VozUsuario)
    valores: list[str] = Field(default_factory=list)
    contexto_vital: dict[str, str] = Field(default_factory=dict)
    historial_coherencia: list[CoherenciaRegistro] = Field(default_factory=list)
