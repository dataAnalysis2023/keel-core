"""Subcomandos: keel alias add | list | borrar."""

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Define atajos para nombres de personas.")
console = Console()


@app.command("add")
def add(
    alias: str = typer.Argument(..., help="Atajo (ej: jc, cliente, el_jefe)"),
    persona: str = typer.Argument(..., help="Nombre real de la persona en keel"),
) -> None:
    """Define un alias para una persona. 'keel conversar --persona jc' equivale a '--persona Juan Carlos'."""
    from keel.storage.local import cargar_aliases, guardar_aliases, keel_dir

    alias_lower = alias.lower()

    # Advertir si el alias coincide con una persona existente
    personas_dir = keel_dir() / "personas"
    if (personas_dir / f"{alias_lower}.json").exists():
        console.print(f"[yellow]⚠ Ya existe una persona llamada '{alias}'. El alias podría no ser necesario.[/yellow]")

    aliases = cargar_aliases()
    existia = alias_lower in aliases
    aliases[alias_lower] = persona
    guardar_aliases(aliases)

    if existia:
        console.print(f"[green]✓ Alias actualizado: '{alias}' → '{persona}'[/green]")
    else:
        console.print(f"[green]✓ Alias creado: '{alias}' → '{persona}'[/green]")


@app.command("list")
def list_aliases() -> None:
    """Lista todos los alias definidos."""
    from keel.storage.local import cargar_aliases

    aliases = cargar_aliases()

    if not aliases:
        console.print("[yellow]No hay alias definidos.[/yellow]")
        console.print("[dim]Usa 'keel alias add <atajo> <persona>' para crear uno.[/dim]")
        return

    tabla = Table(show_lines=False)
    tabla.add_column("Alias", style="bold cyan")
    tabla.add_column("→ Persona")

    for alias, persona in sorted(aliases.items()):
        tabla.add_row(alias, persona)

    console.print(tabla)
    console.print(f"\n[dim]{len(aliases)} alias definido(s).[/dim]")


@app.command("borrar")
def borrar(
    alias: str = typer.Argument(..., help="Alias a eliminar"),
) -> None:
    """Elimina un alias."""
    from keel.storage.local import cargar_aliases, guardar_aliases

    aliases = cargar_aliases()
    alias_lower = alias.lower()

    if alias_lower not in aliases:
        console.print(f"[red]Alias '{alias}' no encontrado.[/red]")
        raise typer.Exit(1)

    persona = aliases.pop(alias_lower)
    guardar_aliases(aliases)
    console.print(f"[green]✓ Alias '{alias}' → '{persona}' eliminado.[/green]")
