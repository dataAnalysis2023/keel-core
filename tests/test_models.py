import json
from pathlib import Path
from keel.models.perfil import PerfilUsuario
from keel.models.persona import Persona

FIXTURES = Path(__file__).parent / "fixtures"


def test_perfil_carga_desde_json():
    data = json.loads((FIXTURES / "perfil_usuario.json").read_text())
    perfil = PerfilUsuario.model_validate(data)
    assert perfil.nombre == "Juan Diego"
    assert "impacto social" in perfil.valores
    assert perfil.voz.registro == "informal"


def test_persona_carga_desde_json():
    data = json.loads((FIXTURES / "persona_ejemplo.json").read_text())
    persona = Persona.model_validate(data)
    assert persona.nombre == "Carlos"
    assert len(persona.promesas_pendientes) == 1
    assert persona.promesas_pendientes[0].descripcion.startswith("Enviar")


def test_persona_defaults_vacios():
    persona = Persona(nombre="Desconocido")
    assert persona.tono_relacional == "neutro"
    assert persona.historial_conversaciones == []
    assert persona.promesas_pendientes == []
