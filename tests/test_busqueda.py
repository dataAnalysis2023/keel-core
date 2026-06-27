"""Tests de keel.engine.busqueda."""

import pytest

from keel.engine.busqueda import buscar_global, _buscar_keywords, _buscar_semantico
from keel.models.persona import Persona, ConversacionResumen


def _persona(nombre, conversaciones):
    convs = [
        ConversacionResumen(fecha=f, resumen=r, temas=t)
        for f, r, t in conversaciones
    ]
    return Persona(nombre=nombre, historial_conversaciones=convs)


PERSONAS = [
    _persona("Carlos", [
        ("2026-06-01", "Cerramos el contrato de suministro", ["contrato", "legal"]),
        ("2026-06-10", "Revisamos el roadmap del producto", ["producto", "roadmap"]),
    ]),
    _persona("María", [
        ("2026-06-05", "Hablamos del lanzamiento del producto", ["producto", "lanzamiento"]),
        ("2026-06-15", "Revisamos el presupuesto anual", ["finanzas", "presupuesto"]),
    ]),
    _persona("Ana", [
        ("2026-06-20", "Discutimos el contrato de servicios", ["contrato", "servicios"]),
    ]),
]


# ── búsqueda keyword ──────────────────────────────────────────────────────────

def test_keyword_encuentra_coincidencia_en_resumen():
    resultados = _buscar_keywords("contrato", PERSONAS, top=10)
    personas = [r["persona"] for r in resultados]
    assert "Carlos" in personas
    assert "Ana" in personas


def test_keyword_encuentra_coincidencia_en_temas():
    resultados = _buscar_keywords("roadmap", PERSONAS, top=10)
    assert len(resultados) == 1
    assert resultados[0]["persona"] == "Carlos"


def test_keyword_sin_coincidencia_devuelve_vacio():
    resultados = _buscar_keywords("kubernetes", PERSONAS, top=10)
    assert resultados == []


def test_keyword_case_insensitive():
    resultados = _buscar_keywords("PRODUCTO", PERSONAS, top=10)
    assert len(resultados) >= 2


def test_keyword_respeta_top():
    resultados = _buscar_keywords("contrato", PERSONAS, top=1)
    assert len(resultados) == 1


def test_keyword_modo_en_resultados():
    resultados = _buscar_keywords("contrato", PERSONAS, top=5)
    assert all(r["modo"] == "keyword" for r in resultados)


# ── buscar_global (modo keyword) ──────────────────────────────────────────────

def test_global_sin_embedder_usa_keyword():
    resultados = buscar_global("producto", PERSONAS, embedder=None, top=5)
    assert len(resultados) >= 1
    assert all(r["modo"] == "keyword" for r in resultados)


def test_global_filtro_persona():
    resultados = buscar_global("contrato", PERSONAS, embedder=None, filtro_persona="Ana")
    assert all(r["persona"] == "Ana" for r in resultados)


def test_global_filtro_persona_case_insensitive():
    resultados = buscar_global("contrato", PERSONAS, embedder=None, filtro_persona="ana")
    assert len(resultados) == 1


def test_global_sin_resultados():
    resultados = buscar_global("nada_que_coincida_xyz", PERSONAS, embedder=None)
    assert resultados == []


def test_global_ordenados_por_fecha_descendente():
    resultados = buscar_global("contrato", PERSONAS, embedder=None, top=10)
    fechas = [r["fecha"] for r in resultados]
    assert fechas == sorted(fechas, reverse=True)


# ── filtros de fecha ──────────────────────────────────────────────────────────

def test_filtro_desde_excluye_anteriores():
    resultados = buscar_global("producto", PERSONAS, desde="2026-04-01")
    for r in resultados:
        assert r["fecha"] >= "2026-04-01"


def test_filtro_hasta_excluye_posteriores():
    resultados = buscar_global("producto", PERSONAS, hasta="2026-02-28")
    for r in resultados:
        assert r["fecha"] <= "2026-02-28"


def test_filtro_rango():
    resultados = buscar_global("reunión", PERSONAS, desde="2026-02-01", hasta="2026-04-30")
    for r in resultados:
        assert "2026-02-01" <= r["fecha"] <= "2026-04-30"


def test_filtro_desde_sin_resultados():
    resultados = buscar_global("producto", PERSONAS, desde="2030-01-01")
    assert resultados == []


def test_filtro_combina_con_persona():
    resultados = buscar_global("producto", PERSONAS, filtro_persona="Carlos", desde="2026-04-01")
    for r in resultados:
        assert r["persona"] == "Carlos"
        assert r["fecha"] >= "2026-04-01"


# ── búsqueda semántica (mock embedder) ───────────────────────────────────────

def test_semantico_llama_buscar_similar(monkeypatch):
    llamadas = []

    def _mock_buscar(persona, texto, embedder, n):
        llamadas.append(persona)
        return []

    import keel.engine.busqueda as mod
    monkeypatch.setattr(mod, "buscar_similar", _mock_buscar)

    class _Emb:
        def embed(self, t): return [0.1] * 10
        def dimension(self): return 10

    buscar_global("producto", PERSONAS, embedder=_Emb(), top=3)
    assert set(llamadas) == {"Carlos", "María", "Ana"}
