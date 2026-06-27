from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/aprendizaje", tags=["aprendizaje"])


@router.post("/analizar")
def analizar():
    """Analiza historial y devuelve sugerencias de actualización al perfil."""
    from keel.storage.local import cargar_perfil, keel_dir
    from keel.models.persona import Persona
    from keel.engine.aprendizaje import analizar_historial
    from keel.llm.ollama import OllamaLLM

    try:
        perfil = cargar_perfil()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Perfil no encontrado. Ejecuta `keel init`.")

    llm = OllamaLLM()
    if not llm.disponible():
        raise HTTPException(status_code=503, detail="Ollama no disponible.")

    personas_dir = keel_dir() / "personas"
    archivos = sorted(personas_dir.glob("*.json")) if personas_dir.exists() else []

    conversaciones: dict[str, list[str]] = {}
    for archivo in archivos:
        p = Persona.model_validate_json(archivo.read_text())
        resumenes = [c.resumen for c in p.historial_conversaciones if c.resumen]
        if len(resumenes) >= 2:
            conversaciones[p.nombre] = resumenes

    if not conversaciones:
        return {"sugerencias": None, "mensaje": "Sin historial suficiente (mínimo 2 conversaciones por persona)."}

    sugerencias = analizar_historial(perfil, conversaciones, llm)
    return {"sugerencias": sugerencias.model_dump()}
