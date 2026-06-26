from fastapi import APIRouter
from keel.api.schemas import StatusResponse

router = APIRouter(tags=["sistema"])


@router.get("/status", response_model=StatusResponse)
def status():
    from keel.llm.ollama import OllamaLLM
    from keel.storage.local import keel_dir
    from keel.storage.vectorial import total_indexados

    d = keel_dir()
    llm = OllamaLLM()

    return StatusResponse(
        ollama=llm.disponible(),
        perfil=(d / "perfil.json").exists(),
        personas=len(list((d / "personas").glob("*.json"))) if (d / "personas").exists() else 0,
        vectores=total_indexados(),
        modelos=llm.modelos_disponibles() if llm.disponible() else [],
    )
