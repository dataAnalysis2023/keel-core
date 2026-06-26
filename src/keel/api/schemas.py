"""Schemas de request/response para la API REST."""

from pydantic import BaseModel
from typing import Optional


# --- Respond ---

class RespondRequest(BaseModel):
    mensaje: str
    remitente: str
    modelo: Optional[str] = None
    sin_vectores: bool = False


class RespondResponse(BaseModel):
    sugerencia: str
    tono: str
    modo_contexto: str  # "semántico" | "cronológico" | "sin historial"


# --- Personas ---

class PersonaUpdate(BaseModel):
    rol: Optional[str] = None
    como_nos_conocemos: Optional[str] = None
    tono_relacional: Optional[str] = None
    sensibilidades: Optional[list[str]] = None


class PersonaResumen(BaseModel):
    nombre: str
    rol: str
    tono_relacional: str
    total_conversaciones: int
    total_promesas: int
    ultima_interaccion: Optional[str]


# --- Remember ---

class RememberRequest(BaseModel):
    nota: str
    persona: Optional[str] = None
    temas: list[str] = []


# --- Status ---

class StatusResponse(BaseModel):
    ollama: bool
    perfil: bool
    personas: int
    vectores: int
    modelos: list[str]
