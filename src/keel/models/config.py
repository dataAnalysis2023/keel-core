from pydantic import BaseModel, Field


class ConfigKeel(BaseModel):
    vault_obsidian: str = ""               # ruta al vault; "" = ~/Proyectos
    modelo_ollama: str = ""                # modelo LLM; "" = default del LLM
    dias_promesa: int = 7                  # umbral agenda notificar / reflexionar
    dias_silencio: int = 14               # umbral personas sin contacto
    min_conversaciones_aprendizaje: int = 2
    clipboard_no_guardar: bool = False     # keel clip --no-guardar por defecto
