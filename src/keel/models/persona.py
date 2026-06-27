"""Módulo 2 — Grafo de relaciones: una Persona conocida."""

from pydantic import BaseModel, Field
from typing import Optional


class PromesaPendiente(BaseModel):
    descripcion: str
    fecha_compromiso: Optional[str] = None  # YYYY-MM-DD


class ConversacionResumen(BaseModel):
    fecha: str  # YYYY-MM-DD
    resumen: str
    temas: list[str] = Field(default_factory=list)


class Persona(BaseModel):
    nombre: str
    rol: str = ""
    como_nos_conocemos: str = ""
    tono_relacional: str = "neutro"  # formal | informal | cercano | distante | neutro
    sensibilidades: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    historial_conversaciones: list[ConversacionResumen] = Field(default_factory=list)
    promesas_pendientes: list[PromesaPendiente] = Field(default_factory=list)
    ultima_interaccion: Optional[str] = None  # YYYY-MM-DD
    estado_actual: str = ""
    # Síntesis inferida — generada por el LLM, no escrita por el usuario
    narrativa: str = ""
    tipo_relacion: str = ""  # familia | amistad | trabajo | cliente | colaborador | nuevo | otro
    contexto_situacional: str = ""  # contexto coyuntural inferido
    ultima_sintesis: Optional[str] = None  # YYYY-MM-DD del último ciclo
