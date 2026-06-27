"""Utilidades compartidas entre comandos CLI."""

from pathlib import Path

from rich.console import Console
from rich.table import Table


def seleccionar_remitente(console: Console, keel_dir: Path) -> str:
    """Muestra lista de personas conocidas y devuelve el nombre elegido."""
    personas_dir = keel_dir / "personas"
    archivos = sorted(personas_dir.glob("*.json")) if personas_dir.exists() else []

    if not archivos:
        console.print("[yellow]No hay personas registradas. Usa `keel persona add`.[/yellow]")
        raise SystemExit(1)

    from keel.models.persona import Persona

    personas = [Persona.model_validate_json(a.read_text()) for a in archivos]

    tabla = Table(show_header=True, box=None, padding=(0, 2))
    tabla.add_column("#", style="dim", width=3)
    tabla.add_column("Nombre", style="bold")
    tabla.add_column("Rol", style="dim")
    tabla.add_column("Última interacción", style="dim")

    for i, p in enumerate(personas, 1):
        tabla.add_row(
            str(i),
            p.nombre,
            p.rol or "—",
            p.ultima_interaccion or "sin interacciones",
        )

    console.print()
    console.print(tabla)

    from rich.prompt import Prompt

    eleccion = Prompt.ask("\n¿Con quién?", default="1")

    # Acepta número o nombre directo
    if eleccion.isdigit():
        idx = int(eleccion) - 1
        if 0 <= idx < len(personas):
            return personas[idx].nombre
        console.print("[red]Número fuera de rango.[/red]")
        raise SystemExit(1)

    # Búsqueda por nombre (case-insensitive, prefijo)
    coincidencias = [p for p in personas if p.nombre.lower().startswith(eleccion.lower())]
    if len(coincidencias) == 1:
        return coincidencias[0].nombre
    if len(coincidencias) > 1:
        console.print(f"[yellow]Ambiguo: {', '.join(p.nombre for p in coincidencias)}[/yellow]")
        raise SystemExit(1)

    console.print(f"[red]No se encontró una persona llamada '{eleccion}'.[/red]")
    raise SystemExit(1)
