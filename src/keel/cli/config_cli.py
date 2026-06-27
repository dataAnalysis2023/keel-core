"""Subcomandos: keel config ver | set | reset."""

import typer
from rich.console import Console
from rich.table import Table

from keel.storage.local import cargar_config, guardar_config
from keel.models.config import ConfigKeel

app = typer.Typer(help="Gestiona las preferencias de keel.")
console = Console()

_CLAVES_VALIDAS = {
    "vault_obsidian": ("str", "Ruta al vault de Obsidian (vacío = ~/Proyectos)"),
    "modelo_ollama": ("str", "Modelo Ollama por defecto (vacío = qwen2.5-coder:7b)"),
    "dias_promesa": ("int", "Días de antelación para alertas de promesas"),
    "dias_silencio": ("int", "Días sin contacto para alertas de personas"),
    "min_conversaciones_aprendizaje": ("int", "Mínimo de conversaciones para análisis de perfil"),
    "clipboard_no_guardar": ("bool", "keel clip no guarda historial por defecto"),
}


@app.command("ver")
def ver() -> None:
    """Muestra la configuración actual."""
    config = cargar_config()
    data = config.model_dump()

    tabla = Table(show_header=True, box=None, padding=(0, 2))
    tabla.add_column("Clave", style="bold cyan")
    tabla.add_column("Valor")
    tabla.add_column("Descripción", style="dim")

    for clave, (tipo, desc) in _CLAVES_VALIDAS.items():
        valor = data.get(clave, "")
        valor_str = str(valor) if valor != "" else "[dim](default)[/dim]"
        tabla.add_row(clave, valor_str, desc)

    console.print()
    console.print(tabla)
    console.print(f"\n[dim]Config en: ~/.keel/config.json[/dim]")


@app.command("set")
def set_config(
    clave: str = typer.Argument(..., help="Nombre de la preferencia"),
    valor: str = typer.Argument(..., help="Nuevo valor"),
) -> None:
    """Establece una preferencia. Ejemplo: keel config set vault_obsidian ~/Notas"""
    if clave not in _CLAVES_VALIDAS:
        claves = ", ".join(_CLAVES_VALIDAS.keys())
        console.print(f"[red]Clave desconocida '{clave}'. Claves válidas: {claves}[/red]")
        raise typer.Exit(1)

    tipo, _ = _CLAVES_VALIDAS[clave]
    config = cargar_config()

    try:
        if tipo == "int":
            setattr(config, clave, int(valor))
        elif tipo == "bool":
            setattr(config, clave, valor.lower() in ("true", "1", "sí", "si", "yes"))
        else:
            setattr(config, clave, valor)
    except ValueError:
        console.print(f"[red]Valor inválido para {clave} (tipo {tipo}): '{valor}'[/red]")
        raise typer.Exit(1)

    guardar_config(config)
    console.print(f"[green]✓ {clave} = {getattr(config, clave)}[/green]")


@app.command("reset")
def reset() -> None:
    """Restaura todos los valores a sus defaults."""
    from rich.prompt import Confirm
    if not Confirm.ask("¿Restaurar configuración a valores por defecto?", default=False):
        console.print("[dim]Cancelado.[/dim]")
        raise typer.Exit(0)

    guardar_config(ConfigKeel())
    console.print("[green]✓ Configuración restaurada a defaults.[/green]")
