"""Motor de sugerencias relacionales: quién contactar y por qué."""

from datetime import date, timedelta
from dataclasses import dataclass, field

from keel.models.persona import Persona


@dataclass
class SugerenciaContacto:
    persona: str
    razones: list[str] = field(default_factory=list)
    urgencia: int = 0  # mayor = más urgente


def sugerir_contactos(
    personas: list[Persona],
    hoy: date | None = None,
    top: int = 3,
    dias_silencio: int = 14,
    dias_promesa: int = 7,
) -> list[SugerenciaContacto]:
    """Devuelve las N personas más prioritarias para contactar hoy."""
    hoy = hoy or date.today()
    sugerencias: list[SugerenciaContacto] = []

    for persona in personas:
        razones: list[str] = []
        urgencia = 0

        # Promesas vencidas
        for pr in persona.promesas_pendientes:
            if not pr.fecha_compromiso:
                continue
            try:
                fecha = date.fromisoformat(pr.fecha_compromiso)
            except ValueError:
                continue
            dias_restantes = (fecha - hoy).days
            if dias_restantes < 0:
                razones.append(f"Promesa vencida hace {abs(dias_restantes)}d: «{pr.descripcion}»")
                urgencia += 100 + abs(dias_restantes)
            elif dias_restantes <= dias_promesa:
                razones.append(f"Promesa próxima en {dias_restantes}d: «{pr.descripcion}»")
                urgencia += 50 - dias_restantes

        # Silencio relacional
        if persona.ultima_interaccion:
            try:
                ultima = date.fromisoformat(persona.ultima_interaccion)
                dias = (hoy - ultima).days
                if dias >= dias_silencio:
                    razones.append(f"{dias} días sin contacto (última vez: {persona.ultima_interaccion})")
                    urgencia += min(dias, 60)
            except ValueError:
                pass

        # Temas frecuentes como contexto (no añaden urgencia, enriquecen el porqué)
        temas = _temas_frecuentes(persona)
        if temas and razones:
            razones.append(f"Temas habituales: {', '.join(temas[:3])}")

        if razones:
            sugerencias.append(SugerenciaContacto(
                persona=persona.nombre,
                razones=razones,
                urgencia=urgencia,
            ))

    sugerencias.sort(key=lambda s: -s.urgencia)
    return sugerencias[:top]


def sugerencias_a_texto(sugerencias: list[SugerenciaContacto]) -> str:
    if not sugerencias:
        return "Sin contactos urgentes en este momento."
    lineas = []
    for i, s in enumerate(sugerencias, 1):
        lineas.append(f"{i}. **{s.persona}**")
        for r in s.razones:
            lineas.append(f"   - {r}")
    return "\n".join(lineas)


def construir_prompt_sugerencias(sugerencias: list[SugerenciaContacto], perfil_nombre: str) -> str:
    if not sugerencias:
        return ""
    datos = sugerencias_a_texto(sugerencias)
    return (
        f"Eres el asistente personal de {perfil_nombre}. "
        f"Basándote en estos datos relacionales, escribe en 2-4 líneas qué debería priorizar esta semana y por qué. "
        f"Sé directo. Sin listas.\n\n{datos}"
    )


def _temas_frecuentes(persona: Persona, top: int = 3) -> list[str]:
    from collections import Counter
    contador: Counter = Counter()
    for conv in persona.historial_conversaciones:
        for tema in conv.temas:
            if tema.strip():
                contador[tema.strip().lower()] += 1
    return [t for t, n in contador.most_common(top) if n > 1]
