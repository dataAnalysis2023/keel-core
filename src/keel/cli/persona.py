"""Subcomandos: keel persona add | list | show | edit."""

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from keel.storage.local import cargar_persona, guardar_persona, keel_dir
from keel.models.persona import Persona

app = typer.Typer(help="Gestiona el grafo de relaciones.")
console = Console()


@app.command("add")
def add(
    nombre: str = typer.Argument(..., help="Nombre de la persona"),
    rol: str = typer.Option("", "--rol", "-r"),
    como: str = typer.Option("", "--como", "-c", help="Cómo se conocen"),
    tono: str = typer.Option("neutro", "--tono", "-t", help="formal|informal|cercano|distante|neutro"),
    sensibilidades: str = typer.Option("", "--sensible", "-s", help="Sensibilidades separadas por coma"),
) -> None:
    """Agrega o actualiza una persona en el grafo de relaciones."""
    persona = cargar_persona(nombre)

    if rol:
        persona.rol = rol
    if como:
        persona.como_nos_conocemos = como
    if tono:
        persona.tono_relacional = tono
    if sensibilidades:
        persona.sensibilidades = [s.strip() for s in sensibilidades.split(",") if s.strip()]

    guardar_persona(persona)
    console.print(f"[green]✓ {nombre} guardado en el grafo de relaciones.[/green]")
    console.print(f"[dim]Archivo: {keel_dir() / 'personas' / f'{nombre.lower()}.json'}[/dim]")


@app.command("list")
def list_personas() -> None:
    """Lista todas las personas registradas."""
    personas_dir = keel_dir() / "personas"
    archivos = sorted(personas_dir.glob("*.json")) if personas_dir.exists() else []

    if not archivos:
        console.print("[yellow]No hay personas registradas. Usa: keel persona add Nombre[/yellow]")
        return

    tabla = Table(title="Grafo de relaciones", show_lines=False)
    tabla.add_column("Nombre", style="bold")
    tabla.add_column("Rol")
    tabla.add_column("Tono")
    tabla.add_column("Conversaciones")
    tabla.add_column("Promesas")

    for archivo in archivos:
        p = Persona.model_validate_json(archivo.read_text())
        tabla.add_row(
            p.nombre,
            p.rol or "—",
            p.tono_relacional,
            str(len(p.historial_conversaciones)),
            str(len(p.promesas_pendientes)),
        )

    console.print(tabla)


@app.command("show")
def show(nombre: str = typer.Argument(...)) -> None:
    """Muestra el perfil completo de una persona."""
    persona = cargar_persona(nombre)
    console.print(
        Panel(
            persona.model_dump_json(indent=2),
            title=f"[bold]{persona.nombre}[/bold]",
            border_style="blue",
        )
    )
