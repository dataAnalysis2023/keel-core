from pydantic import BaseModel


class ConfigKeel(BaseModel):
    vault_obsidian: str = ""               # ruta al vault; "" = ~/Proyectos
    modelo_ollama: str = ""                # modelo Ollama; "" = default del proveedor
    dias_promesa: int = 7                  # umbral agenda notificar / reflexionar
    dias_silencio: int = 14               # umbral personas sin contacto
    min_conversaciones_aprendizaje: int = 2
    clipboard_no_guardar: bool = False     # keel clip --no-guardar por defecto
    proveedor: str = "ollama"              # ollama | anthropic | openai
    modelo_cloud: str = ""                 # modelo cloud; "" = default del proveedor
