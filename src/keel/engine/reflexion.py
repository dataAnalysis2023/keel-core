"""Motor de reflexión semanal: sintetiza el estado relacional del usuario."""

from collections import Counter
from datetime import date, timedelta

from keel.models.persona import Persona
from keel.models.reflexion import DigestRelacional, PersonaSinContacto, PromesaProxima


def construir_digest(
    personas: list[Persona],
    hoy: date | None = None,
    dias_promesa: int = 7,
    dias_sin_contacto: int = 14,
) -> DigestRelacional:
    """Analiza todas las personas y devuelve un digest relacional.

    Args:
        personas: lista completa de personas cargadas desde ~/.keel/personas/
        hoy: fecha de referencia (inyectable para tests)
        dias_promesa: alerta si la promesa vence en <= N días
        dias_sin_contacto: alerta si no hubo contacto en >= N días
    """
    hoy = hoy or date.today()

    promesas = _promesas_proximas(personas, hoy, dias_promesa)
    sin_contacto = _personas_sin_contacto(personas, hoy, dias_sin_contacto)
    temas = _temas_recurrentes(personas)

    return DigestRelacional(
        fecha=hoy.isoformat(),
        promesas_proximas=promesas,
        personas_sin_contacto=sin_contacto,
        temas_recurrentes=temas,
    )


def construir_sintesis(digest: DigestRelacional, perfil_nombre: str, llm) -> str:
    """Genera una síntesis narrativa del digest vía LLM."""
    if not (digest.promesas_proximas or digest.personas_sin_contacto or digest.temas_recurrentes):
        return "Sin compromisos urgentes ni patrones destacados esta semana."

    prompt = _prompt_sintesis(digest, perfil_nombre)
    return llm.generar(prompt)


def digest_a_markdown(digest: DigestRelacional, sintesis: str = "") -> str:
    """Convierte el digest a Markdown listo para Obsidian o clipboard."""
    lineas = [f"# Reflexión semanal — {digest.fecha}\n"]

    if sintesis:
        lineas.append(f"{sintesis}\n")

    if digest.promesas_proximas:
        lineas.append("## Compromisos próximos\n")
        for p in sorted(digest.promesas_proximas, key=lambda x: x.dias_restantes):
            urgencia = "🔴" if p.dias_restantes <= 2 else ("🟡" if p.dias_restantes <= 5 else "🟢")
            dias = f"{p.dias_restantes}d" if p.dias_restantes >= 0 else f"VENCIDO ({abs(p.dias_restantes)}d)"
            lineas.append(f"- {urgencia} **{p.persona}** — {p.descripcion} `{dias}`")
        lineas.append("")

    if digest.personas_sin_contacto:
        lineas.append("## Sin contacto reciente\n")
        for p in sorted(digest.personas_sin_contacto, key=lambda x: -x.dias_sin_contacto):
            lineas.append(f"- **{p.nombre}** — última vez hace {p.dias_sin_contacto} días ({p.ultima_interaccion})")
        lineas.append("")

    if digest.temas_recurrentes:
        lineas.append("## Temas recurrentes\n")
        lineas.append(", ".join(f"`{t}`" for t in digest.temas_recurrentes))
        lineas.append("")

    return "\n".join(lineas)


# ── funciones privadas ────────────────────────────────────────────────────────

def _promesas_proximas(
    personas: list[Persona], hoy: date, ventana: int
) -> list[PromesaProxima]:
    resultado = []
    limite = hoy + timedelta(days=ventana)

    for persona in personas:
        for promesa in persona.promesas_pendientes:
            if not promesa.fecha_compromiso:
                continue
            try:
                fecha = date.fromisoformat(promesa.fecha_compromiso)
            except ValueError:
                continue
            if fecha <= limite:
                resultado.append(
                    PromesaProxima(
                        persona=persona.nombre,
                        descripcion=promesa.descripcion,
                        fecha_limite=promesa.fecha_compromiso,
                        dias_restantes=(fecha - hoy).days,
                    )
                )
    return resultado


def _personas_sin_contacto(
    personas: list[Persona], hoy: date, umbral: int
) -> list[PersonaSinContacto]:
    resultado = []
    for persona in personas:
        if not persona.ultima_interaccion:
            continue
        try:
            ultima = date.fromisoformat(persona.ultima_interaccion)
        except ValueError:
            continue
        dias = (hoy - ultima).days
        if dias >= umbral:
            resultado.append(
                PersonaSinContacto(
                    nombre=persona.nombre,
                    ultima_interaccion=persona.ultima_interaccion,
                    dias_sin_contacto=dias,
                )
            )
    return resultado


def _temas_recurrentes(personas: list[Persona], top: int = 5) -> list[str]:
    contador: Counter = Counter()
    for persona in personas:
        for conv in persona.historial_conversaciones:
            for tema in conv.temas:
                if tema.strip():
                    contador[tema.strip().lower()] += 1
    return [tema for tema, _ in contador.most_common(top) if contador[tema] > 1]


def _prompt_sintesis(digest: DigestRelacional, nombre: str) -> str:
    partes = [f"Eres el asistente personal de {nombre}. Resume en 3-4 líneas el estado de sus relaciones esta semana.\n"]

    if digest.promesas_proximas:
        items = "; ".join(f"{p.persona}: {p.descripcion} ({p.dias_restantes}d)" for p in digest.promesas_proximas)
        partes.append(f"Compromisos próximos: {items}")

    if digest.personas_sin_contacto:
        items = "; ".join(f"{p.nombre} ({p.dias_sin_contacto}d sin contacto)" for p in digest.personas_sin_contacto)
        partes.append(f"Personas sin contacto reciente: {items}")

    if digest.temas_recurrentes:
        partes.append(f"Temas recurrentes: {', '.join(digest.temas_recurrentes)}")

    partes.append("\nSé directo. Sin listas, sin encabezados. Solo el resumen ejecutivo.")
    return "\n".join(partes)
