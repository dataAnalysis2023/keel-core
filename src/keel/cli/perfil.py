"""Subgrupo CLI: keel perfil show | actualizar."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

app = typer.Typer(help="Gestiona el perfil del usuario.")
console = Console()


@app.command()
def show() -> None:
    """Muestra el perfil actual del usuario."""
    from keel.storage.local import cargar_perfil

    try:
        perfil = cargar_perfil()
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    tabla = Table(show_header=False, box=None, padding=(0, 2))
    tabla.add_column("Campo", style="bold cyan")
    tabla.add_column("Valor")

    tabla.add_row("Nombre", perfil.nombre)
    tabla.add_row("Tono", perfil.voz.tono or "—")
    tabla.add_row("Registro", perfil.voz.registro)
    tabla.add_row(
        "Frases características",
        "\n".join(f"• {f}" for f in perfil.voz.frases_caracteristicas) or "—",
    )
    tabla.add_row(
        "Vocabulario frecuente",
        ", ".join(perfil.voz.vocabulario_frecuente) or "—",
    )
    tabla.add_row(
        "Valores",
        ", ".join(perfil.valores) or "—",
    )
    if perfil.contexto_vital:
        ctx = "\n".join(f"{k}: {v}" for k, v in perfil.contexto_vital.items())
        tabla.add_row("Contexto vital", ctx)

    console.print(Panel(tabla, title="[bold]Perfil de usuario[/bold]", border_style="cyan"))


@app.command()
def editar() -> None:
    """Abre el perfil del usuario en $EDITOR para edición directa."""
    import os
    import subprocess
    from keel.storage.local import keel_dir
    from keel.models.perfil import PerfilUsuario

    ruta = keel_dir() / "perfil.json"

    if not ruta.exists():
        console.print("[red]Perfil no encontrado. Ejecuta `keel init` primero.[/red]")
        raise typer.Exit(1)

    editor = os.environ.get("EDITOR", "nano")
    subprocess.run([editor, str(ruta)])

    try:
        PerfilUsuario.model_validate_json(ruta.read_text())
        console.print("[green]✓ Perfil guardado correctamente.[/green]")
    except Exception as e:
        console.print(f"[red]El JSON editado no es válido: {e}[/red]")
        console.print("[yellow]El archivo se guardó — revísalo con `keel perfil show`.[/yellow]")


@app.command()
def actualizar(
    modelo: str = typer.Option(None, "--modelo", "-m", help="Modelo Ollama para el análisis"),
    min_conversaciones: int = typer.Option(
        2, "--min", help="Mínimo de conversaciones para incluir una persona"
    ),
) -> None:
    """Analiza el historial y sugiere actualizaciones al perfil."""
    from keel.storage.local import cargar_perfil, guardar_perfil, keel_dir
    from keel.models.persona import Persona
    from keel.engine.aprendizaje import analizar_historial
    from keel.llm.ollama import OllamaLLM

    try:
        perfil = cargar_perfil()
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    llm = OllamaLLM(modelo=modelo) if modelo else OllamaLLM()
    if not llm.disponible():
        console.print("[red]Ollama no disponible. Ejecuta: ollama serve[/red]")
        raise typer.Exit(1)

    # Recopilar historial de todas las personas
    personas_dir = keel_dir() / "personas"
    archivos = sorted(personas_dir.glob("*.json")) if personas_dir.exists() else []

    conversaciones: dict[str, list[str]] = {}
    for archivo in archivos:
        p = Persona.model_validate_json(archivo.read_text())
        resumenes = [c.resumen for c in p.historial_conversaciones if c.resumen]
        if len(resumenes) >= min_conversaciones:
            conversaciones[p.nombre] = resumenes

    total = sum(len(v) for v in conversaciones.values())
    if total == 0:
        console.print(
            f"[yellow]No hay suficiente historial (mínimo {min_conversaciones} conversaciones por persona).[/yellow]"
        )
        raise typer.Exit(0)

    console.print(
        f"\n[dim]Analizando {total} conversaciones con {len(conversaciones)} persona(s)...[/dim]\n"
    )

    sugerencias = analizar_historial(perfil, conversaciones, llm)

    if sugerencias.resumen:
        console.print(Panel(sugerencias.resumen, title="[bold]Análisis[/bold]", border_style="dim"))

    hay_sugerencias = any([
        sugerencias.frases_nuevas,
        sugerencias.vocabulario_nuevo,
        sugerencias.valores_detectados,
        sugerencias.temas_recurrentes,
    ])

    if not hay_sugerencias:
        console.print("[green]El perfil ya refleja bien los patrones detectados.[/green]")
        return

    modificado = False

    # Frases características
    if sugerencias.frases_nuevas:
        console.print("\n[bold]Frases características detectadas:[/bold]")
        for frase in sugerencias.frases_nuevas:
            if frase not in perfil.voz.frases_caracteristicas:
                if Confirm.ask(f'  Agregar "[cyan]{frase}[/cyan]"?', default=True):
                    perfil.voz.frases_caracteristicas.append(frase)
                    modificado = True

    # Vocabulario frecuente
    if sugerencias.vocabulario_nuevo:
        console.print("\n[bold]Vocabulario frecuente detectado:[/bold]")
        for term in sugerencias.vocabulario_nuevo:
            if term not in perfil.voz.vocabulario_frecuente:
                if Confirm.ask(f'  Agregar "[cyan]{term}[/cyan]" al vocabulario?', default=True):
                    perfil.voz.vocabulario_frecuente.append(term)
                    modificado = True

    # Valores
    if sugerencias.valores_detectados:
        console.print("\n[bold]Valores inferidos del historial:[/bold]")
        for valor in sugerencias.valores_detectados:
            if valor not in perfil.valores:
                if Confirm.ask(f'  Agregar valor "[cyan]{valor}[/cyan]"?', default=True):
                    perfil.valores.append(valor)
                    modificado = True

    # Temas recurrentes → contexto vital
    if sugerencias.temas_recurrentes:
        console.print("\n[bold]Temas recurrentes (informativo, no se agregan al perfil):[/bold]")
        for tema in sugerencias.temas_recurrentes:
            console.print(f"  [dim]• {tema}[/dim]")

    if modificado:
        guardar_perfil(perfil)
        console.print("\n[green]✓ Perfil actualizado.[/green]")
    else:
        console.print("\n[dim]Sin cambios aplicados.[/dim]")
