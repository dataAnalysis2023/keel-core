"""Estadísticas del grafo relacional."""

from collections import Counter, defaultdict
from datetime import date

from keel.models.persona import Persona


def calcular_stats(personas: list[Persona], hoy: date | None = None) -> dict:
    """Devuelve un dict con todas las métricas del grafo."""
    hoy = hoy or date.today()

    total_conversaciones = sum(len(p.historial_conversaciones) for p in personas)
    total_promesas = sum(len(p.promesas_pendientes) for p in personas)

    return {
        "total_personas": len(personas),
        "total_conversaciones": total_conversaciones,
        "total_promesas_pendientes": total_promesas,
        "personas_activas": _personas_activas(personas),
        "temas_frecuentes": _temas_frecuentes(personas),
        "conversaciones_por_mes": _por_mes(personas),
        "promesas_vencidas": _promesas_vencidas(personas, hoy),
        "sin_historial": [p.nombre for p in personas if not p.historial_conversaciones],
    }


def _personas_activas(personas: list[Persona], top: int = 5) -> list[dict]:
    datos = [
        {"nombre": p.nombre, "conversaciones": len(p.historial_conversaciones), "ultima": p.ultima_interaccion or "—"}
        for p in personas
        if p.historial_conversaciones
    ]
    return sorted(datos, key=lambda d: d["conversaciones"], reverse=True)[:top]


def _temas_frecuentes(personas: list[Persona], top: int = 10) -> list[dict]:
    contador: Counter = Counter()
    for p in personas:
        for conv in p.historial_conversaciones:
            for tema in conv.temas:
                if tema.strip():
                    contador[tema.strip().lower()] += 1
    return [{"tema": t, "menciones": n} for t, n in contador.most_common(top)]


def _por_mes(personas: list[Persona]) -> dict[str, int]:
    por_mes: defaultdict[str, int] = defaultdict(int)
    for p in personas:
        for conv in p.historial_conversaciones:
            mes = conv.fecha[:7]  # YYYY-MM
            por_mes[mes] += 1
    return dict(sorted(por_mes.items()))


def _promesas_vencidas(personas: list[Persona], hoy: date) -> list[dict]:
    vencidas = []
    for p in personas:
        for pr in p.promesas_pendientes:
            if not pr.fecha_compromiso:
                continue
            try:
                fecha = date.fromisoformat(pr.fecha_compromiso)
            except ValueError:
                continue
            if fecha < hoy:
                vencidas.append({
                    "persona": p.nombre,
                    "descripcion": pr.descripcion,
                    "fecha": pr.fecha_compromiso,
                    "dias_vencida": (hoy - fecha).days,
                })
    return sorted(vencidas, key=lambda d: -d["dias_vencida"])
