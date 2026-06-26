"""Módulo 3 — Motor de respuesta."""

from keel.models.perfil import PerfilUsuario
from keel.models.persona import Persona
from keel.engine.presencia import analizar_tono
from keel.llm.base import LLMBase


def construir_prompt(
    perfil: PerfilUsuario,
    persona: Persona,
    mensaje: str,
    tono_resumen: str,
) -> str:
    historial = ""
    if persona.historial_conversaciones:
        entradas = [
            f"- {c.fecha}: {c.resumen}"
            for c in persona.historial_conversaciones[-3:]
        ]
        historial = "\nÚltimas conversaciones:\n" + "\n".join(entradas)

    promesas = ""
    if persona.promesas_pendientes:
        items = [f"- {p.descripcion}" for p in persona.promesas_pendientes]
        promesas = "\nPromesas pendientes con esta persona:\n" + "\n".join(items)

    valores = ", ".join(perfil.valores) if perfil.valores else "no especificados"
    frases = (
        ", ".join(f'"{f}"' for f in perfil.voz.frases_caracteristicas)
        if perfil.voz.frases_caracteristicas
        else "ninguna registrada"
    )

    return f"""Eres {perfil.nombre}. Aquí están tus valores y tu forma de comunicarte:

VALORES: {valores}
TONO DE VOZ: {perfil.voz.tono or "directo y claro"}
REGISTRO: {perfil.voz.registro}
FRASES CARACTERÍSTICAS: {frases}

SOBRE {persona.nombre.upper()}:
- Rol: {persona.rol or "no especificado"}
- Cómo se conocen: {persona.como_nos_conocemos or "no registrado"}
- Tono relacional: {persona.tono_relacional}
- Sensibilidades: {", ".join(persona.sensibilidades) or "ninguna registrada"}
{historial}{promesas}

MENSAJE RECIBIDO DE {persona.nombre.upper()}:
"{mensaje}"

TONO DEL MENSAJE: {tono_resumen}

Escribe UNA respuesta en primera persona, como si fueras {perfil.nombre}.
La respuesta debe ser fiel a quien eres, apropiada para tu relación con {persona.nombre},
y considerar el tono emocional del mensaje.
Escribe solo el texto de la respuesta, sin explicaciones ni encabezados."""


def generar_sugerencia(
    perfil: PerfilUsuario,
    persona: Persona,
    mensaje: str,
    llm: LLMBase,
) -> str:
    tono = analizar_tono(mensaje)
    prompt = construir_prompt(perfil, persona, mensaje, tono.resumen)
    return llm.generar(prompt)
