"""CLI de keel."""

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from keel.cli import persona as persona_cli

app = typer.Typer(
    name="keel",
    help="Motor de extensión cognitiva personal.",
    add_completion=False,
)
app.add_typer(persona_cli.app, name="persona")

console = Console()


@app.command()
def respond(
    mensaje: str = typer.Argument(..., help="Mensaje recibido al que responder"),
    remitente: str = typer.Option(..., "--remitente", "-r", help="Nombre del remitente"),
    modelo: str = typer.Option(None, "--modelo", "-m", help="Modelo Ollama (default: configurado en ollama.py)"),
    no_guardar: bool = typer.Option(False, "--no-guardar", help="No ofrecer guardar la conversación"),
) -> None:
    """Genera una sugerencia de respuesta dado un mensaje y su remitente."""
    from keel.storage.local import cargar_perfil, cargar_persona, guardar_persona
    from keel.engine.respuesta import generar_sugerencia
    from keel.engine.presencia import analizar_tono
    from keel.llm.ollama import OllamaLLM
    from keel.models.persona import ConversacionResumen
    from datetime import date

    try:
        perfil = cargar_perfil()
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    persona = cargar_persona(remitente)
    llm = OllamaLLM(modelo=modelo) if modelo else OllamaLLM()

    if not llm.disponible():
        console.print("[red]Ollama no disponible. Ejecuta: ollama serve[/red]")
        raise typer.Exit(1)

    tono = analizar_tono(mensaje)
    console.print(f"\n[dim]Tono detectado: {tono.resumen}[/dim]")
    console.print("[dim]Generando...[/dim]\n")

    sugerencia = generar_sugerencia(perfil, persona, mensaje, llm)

    console.print(
        Panel(
            sugerencia,
            title=f"[bold]Sugerencia para {remitente}[/bold]",
            border_style="blue",
        )
    )

    # Módulo 4 — actualización del grafo de relaciones
    if no_guardar:
        return

    guardar = Confirm.ask("\n¿Guardar esta conversación en el historial?", default=True)
    if not guardar:
        return

    resumen = Prompt.ask(
        "Resumen breve (Enter para usar el mensaje como resumen)",
        default=mensaje[:80],
    )
    temas_raw = Prompt.ask("Temas separados por coma (opcional)", default="")
    temas = [t.strip() for t in temas_raw.split(",") if t.strip()]

    persona.historial_conversaciones.append(
        ConversacionResumen(
            fecha=date.today().isoformat(),
            resumen=resumen,
            temas=temas,
        )
    )
    persona.ultima_interaccion = date.today().isoformat()
    guardar_persona(persona)
    console.print(f"[green]✓ Conversación guardada en el perfil de {remitente}.[/green]")


@app.command()
def init() -> None:
    """Inicializa ~/.keel/ con un perfil de ejemplo."""
    keel_dir = Path.home() / ".keel"
    keel_dir.mkdir(parents=True, exist_ok=True)
    (keel_dir / "personas").mkdir(exist_ok=True)

    perfil_path = keel_dir / "perfil.json"
    if perfil_path.exists():
        console.print(f"[yellow]Ya existe un perfil en {perfil_path}[/yellow]")
        return

    perfil_ejemplo = {
        "nombre": "Tu nombre aquí",
        "voz": {
            "tono": "directo y reflexivo",
            "registro": "informal",
            "vocabulario_frecuente": [],
            "frases_caracteristicas": [],
        },
        "valores": ["claridad", "compromiso", "honestidad"],
        "contexto_vital": {
            "rol": "fundador",
            "organizacion": "Mi empresa",
            "momento_actual": "construcción del producto",
        },
        "historial_coherencia": [],
    }

    perfil_path.write_text(json.dumps(perfil_ejemplo, indent=2, ensure_ascii=False))
    console.print(f"[green]Perfil creado en {perfil_path}[/green]")
    console.print("[dim]Edítalo antes de usar `keel respond`.[/dim]")


@app.command()
def status() -> None:
    """Muestra el estado del sistema: Ollama, perfil, personas."""
    from keel.llm.ollama import OllamaLLM

    keel_dir = Path.home() / ".keel"
    llm = OllamaLLM()
    ollama_ok = llm.disponible()
    perfil_ok = (keel_dir / "perfil.json").exists()
    personas_dir = keel_dir / "personas"
    personas = list(personas_dir.glob("*.json")) if personas_dir.exists() else []

    console.print("\n[bold]Estado de Keel[/bold]\n")
    console.print(f"  Ollama:   {'[green]✓ disponible[/green]' if ollama_ok else '[red]✗ no disponible — ejecuta: ollama serve[/red]'}")
    console.print(f"  Perfil:   {'[green]✓ configurado[/green]' if perfil_ok else '[yellow]⚠ no encontrado — ejecuta: keel init[/yellow]'}")
    console.print(f"  Personas: {len(personas)} registradas")

    if ollama_ok:
        modelos = llm.modelos_disponibles()
        console.print(f"  Modelos:  {', '.join(modelos) if modelos else 'ninguno instalado — ejecuta: ollama pull llama3'}")

    console.print()


if __name__ == "__main__":
    app()
