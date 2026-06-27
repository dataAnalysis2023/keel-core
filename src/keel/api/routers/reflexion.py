from fastapi import APIRouter, Query

router = APIRouter(prefix="/reflexion", tags=["reflexion"])


@router.get("")
def reflexion(
    dias_promesa: int = Query(7, description="Alerta si promesa vence en <= N días"),
    dias_silencio: int = Query(14, description="Alerta si sin contacto en >= N días"),
    formato: str = Query("json", description="json | markdown"),
):
    from keel.storage.local import keel_dir
    from keel.models.persona import Persona
    from keel.engine.reflexion import construir_digest, digest_a_markdown

    personas_dir = keel_dir() / "personas"
    archivos = sorted(personas_dir.glob("*.json")) if personas_dir.exists() else []
    personas_lista = [Persona.model_validate_json(a.read_text()) for a in archivos]

    digest = construir_digest(
        personas_lista,
        dias_promesa=dias_promesa,
        dias_sin_contacto=dias_silencio,
    )

    if formato == "markdown":
        return {"markdown": digest_a_markdown(digest)}

    return digest.model_dump()
