from keel.engine.presencia import analizar_tono
from keel.engine.respuesta import construir_prompt
from keel.models.perfil import PerfilUsuario, VozUsuario
from keel.models.persona import Persona


def test_tono_neutro():
    resultado = analizar_tono("Hola, ¿cómo estás?")
    assert "neutro" in resultado.resumen


def test_tono_urgente():
    resultado = analizar_tono("Necesito esto urgente, ya, por favor inmediato")
    assert resultado.urgencia > 0


def test_tono_formal():
    resultado = analizar_tono("Estimado Juan, le informo que cordialmente respetuosamente...")
    assert resultado.formalidad > 0


def test_construir_prompt_contiene_elementos_clave():
    perfil = PerfilUsuario(
        nombre="Juan",
        voz=VozUsuario(tono="directo", registro="informal"),
        valores=["claridad"],
    )
    persona = Persona(nombre="Carlos", rol="socio")
    prompt = construir_prompt(perfil, persona, "Hola, ¿cómo vas?", "neutro y directo")

    assert "Juan" in prompt
    assert "Carlos" in prompt
    assert "claridad" in prompt
    assert "Hola, ¿cómo vas?" in prompt
    assert "neutro y directo" in prompt


def test_construir_prompt_incluye_promesas():
    from keel.models.persona import PromesaPendiente
    perfil = PerfilUsuario(nombre="Juan")
    persona = Persona(
        nombre="María",
        promesas_pendientes=[PromesaPendiente(descripcion="Enviar el informe")]
    )
    prompt = construir_prompt(perfil, persona, "Hola", "neutro y directo")
    assert "Enviar el informe" in prompt
