from fastapi import APIRouter, HTTPException
from datetime import date

from keel.api.schemas import RespondRequest, RespondResponse, RememberRequest

router = APIRouter(tags=["motor"])


@router.post("/respond", response_model=RespondResponse)
def respond(req: RespondRequest):
    from keel.storage.local import cargar_perfil, cargar_persona
    from keel.engine.respuesta import generar_sugerencia
    from keel.engine.presencia import analizar_tono
    from keel.llm.ollama import OllamaLLM
    from keel.embedder.fastembed import get_embedder

    try:
        perfil = cargar_perfil()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    persona = cargar_persona(req.remitente)
    llm = OllamaLLM(modelo=req.modelo) if req.modelo else OllamaLLM()

    if not llm.disponible():
        raise HTTPException(status_code=503, detail="Ollama no disponible. Ejecuta: ollama serve")

    embedder = None
    modo = "sin historial"

    if not req.sin_vectores:
        try:
            embedder = get_embedder()
            modo = "semántico"
        except Exception:
            pass

    if embedder is None and persona.historial_conversaciones:
        modo = "cronológico"

    tono = analizar_tono(req.mensaje)
    sugerencia = generar_sugerencia(perfil, persona, req.mensaje, llm, embedder)

    return RespondResponse(sugerencia=sugerencia, tono=tono.resumen, modo_contexto=modo)


@router.post("/remember")
def remember(req: RememberRequest):
    from keel.storage.local import cargar_persona, guardar_persona
    from keel.storage.vectorial import indexar_conversacion
    from keel.embedder.fastembed import get_embedder
    from keel.models.persona import ConversacionResumen, PromesaPendiente

    hoy = date.today().isoformat()

    if req.persona:
        p = cargar_persona(req.persona)
        if req.nota.lower().startswith("prometi") or req.nota.lower().startswith("prometí"):
            p.promesas_pendientes.append(PromesaPendiente(descripcion=req.nota, fecha_compromiso=hoy))
        else:
            p.historial_conversaciones.append(
                ConversacionResumen(fecha=hoy, resumen=req.nota, temas=req.temas)
            )
        guardar_persona(p)

    try:
        embedder = get_embedder()
        indexar_conversacion(req.persona or "_global", hoy, req.nota, req.temas, embedder)
        indexado = True
    except Exception:
        indexado = False

    return {"guardado": bool(req.persona), "indexado": indexado}
