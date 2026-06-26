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


def _embedder():
    """Devuelve el embedder singleton. Primera vez descarga el modelo (~120MB)."""
    from keel.embedder.fastembed import get_embedder
    return get_embedder()


@app.command()
def respond(
    mensaje: str = typer.Argument(..., help="Mensaje recibido al que responder"),
    remitente: str = typer.Option(..., "--remitente", "-r", help="Nombre del remitente"),
    modelo: str = typer.Option(None, "--modelo", "-m", help="Modelo Ollama"),
    sin_vectores: bool = typer.Option(False, "--sin-vectores", help="Desactiva búsqueda semántica"),
    no_guardar: bool = typer.Option(False, "--no-guardar", help="No ofrecer guardar la conversación"),
) -> None:
    """Genera una sugerencia de respuesta dado un mensaje y su remitente."""
    from keel.storage.local import cargar_perfil, cargar_persona, guardar_persona
    from keel.engine.respuesta import generar_sugerencia
    from keel.engine.presencia import analizar_tono
    from keel.llm.ollama import OllamaLLM
    from keel.models.persona import ConversacionResumen
    from keel.storage.vectorial import indexar_conversacion
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

    embedder = None
    if not sin_vectores:
        try:
            embedder = _embedder()
        except Exception as e:
            console.print(f"[dim]Embedder no disponible ({e}), usando modo sin vectores.[/dim]")

    tono = analizar_tono(mensaje)
    console.print(f"\n[dim]Tono detectado: {tono.resumen}[/dim]")
    modo = "semántico" if embedder else "cronológico"
    console.print(f"[dim]Contexto: modo {modo} | Generando...[/dim]\n")

    sugerencia = generar_sugerencia(perfil, persona, mensaje, llm, embedder)

    console.print(
        Panel(
            sugerencia,
            title=f"[bold]Sugerencia para {remitente}[/bold]",
            border_style="blue",
        )
    )

    if no_guardar:
        return

    guardar = Confirm.ask("\n¿Guardar esta conversación en el historial?", default=True)
    if not guardar:
        return

    resumen = Prompt.ask(
        "Resumen breve (Enter para usar el mensaje)",
        default=mensaje[:80],
    )
    temas_raw = Prompt.ask("Temas separados por coma (opcional)", default="")
    temas = [t.strip() for t in temas_raw.split(",") if t.strip()]
    hoy = date.today().isoformat()

    # Guarda en JSON
    persona.historial_conversaciones.append(
        ConversacionResumen(fecha=hoy, resumen=resumen, temas=temas)
    )
    persona.ultima_interaccion = hoy
    guardar_persona(persona)

    # Indexa en LanceDB si embedder disponible
    if embedder:
        try:
            indexar_conversacion(remitente, hoy, resumen, temas, embedder)
            console.print(f"[green]✓ Guardado e indexado en el grafo de relaciones.[/green]")
        except Exception as e:
            console.print(f"[yellow]✓ Guardado en JSON. Indexación vectorial falló: {e}[/yellow]")
    else:
        console.print(f"[green]✓ Guardado en el historial de {remitente}.[/green]")


@app.command()
def remember(
    nota: str = typer.Argument(..., help="Nota a recordar"),
    persona: str = typer.Option(None, "--persona", "-p", help="Persona relacionada (opcional)"),
    temas: str = typer.Option("", "--temas", "-t", help="Temas separados por coma"),
) -> None:
    """Agrega una nota al contexto. Opcionalmente la asocia a una persona."""
    from keel.storage.vectorial import indexar_conversacion
    from keel.models.persona import PromesaPendiente
    from keel.storage.local import cargar_persona, guardar_persona
    from datetime import date

    hoy = date.today().isoformat()
    temas_lista = [t.strip() for t in temas.split(",") if t.strip()]
    embedder = None

    try:
        embedder = _embedder()
    except Exception:
        pass

    if persona:
        p = cargar_persona(persona)
        if nota.lower().startswith("prometí") or nota.lower().startswith("prometi"):
            p.promesas_pendientes.append(PromesaPendiente(descripcion=nota, fecha_compromiso=hoy))
            guardar_persona(p)
            console.print(f"[green]✓ Promesa registrada para {persona}.[/green]")
        else:
            from keel.models.persona import ConversacionResumen
            p.historial_conversaciones.append(
                ConversacionResumen(fecha=hoy, resumen=nota, temas=temas_lista)
            )
            guardar_persona(p)
            console.print(f"[green]✓ Nota guardada en el perfil de {persona}.[/green]")

    if embedder:
        try:
            destino = persona or "_global"
            indexar_conversacion(destino, hoy, nota, temas_lista, embedder)
            console.print(f"[dim]Indexado en LanceDB.[/dim]")
        except Exception as e:
            console.print(f"[dim]Indexación vectorial falló: {e}[/dim]")
    elif not persona:
        console.print(f"[yellow]Nota sin persona asociada y sin embedder — no se guardó en ningún lado.[/yellow]")


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
    """Muestra el estado del sistema: Ollama, perfil, personas, índice vectorial."""
    from keel.llm.ollama import OllamaLLM
    from keel.storage.vectorial import total_indexados

    keel_dir = Path.home() / ".keel"
    llm = OllamaLLM()
    ollama_ok = llm.disponible()
    perfil_ok = (keel_dir / "perfil.json").exists()
    personas_dir = keel_dir / "personas"
    personas = list(personas_dir.glob("*.json")) if personas_dir.exists() else []
    indexados = total_indexados()

    console.print("\n[bold]Estado de Keel[/bold]\n")
    console.print(f"  Ollama:    {'[green]✓ disponible[/green]' if ollama_ok else '[red]✗ no disponible — ejecuta: ollama serve[/red]'}")
    console.print(f"  Perfil:    {'[green]✓ configurado[/green]' if perfil_ok else '[yellow]⚠ no encontrado — ejecuta: keel init[/yellow]'}")
    console.print(f"  Personas:  {len(personas)} registradas")
    console.print(f"  Vectores:  {indexados} conversaciones indexadas")

    if ollama_ok:
        modelos = llm.modelos_disponibles()
        console.print(f"  Modelos:   {', '.join(modelos) if modelos else 'ninguno instalado'}")

    console.print()


@app.command()
def agenda() -> None:
    """Muestra todas las promesas pendientes de todas las personas."""
    from keel.storage.local import keel_dir
    from keel.models.persona import Persona
    from rich.table import Table
    from datetime import date

    personas_dir = keel_dir() / "personas"
    archivos = sorted(personas_dir.glob("*.json")) if personas_dir.exists() else []

    pendientes = []
    for archivo in archivos:
        p = Persona.model_validate_json(archivo.read_text())
        for promesa in p.promesas_pendientes:
            pendientes.append((p.nombre, promesa))

    if not pendientes:
        console.print("[green]Sin promesas pendientes.[/green]")
        return

    tabla = Table(title="Agenda de compromisos", show_lines=True)
    tabla.add_column("Con quién", style="bold")
    tabla.add_column("Compromiso")
    tabla.add_column("Fecha límite")

    hoy = date.today().isoformat()
    for nombre, promesa in pendientes:
        vencida = promesa.fecha_compromiso and promesa.fecha_compromiso < hoy
        fecha_str = f"[red]{promesa.fecha_compromiso}[/red]" if vencida else (promesa.fecha_compromiso or "—")
        tabla.add_row(nombre, promesa.descripcion, fecha_str)

    console.print(tabla)
    console.print(f"\n[dim]{len(pendientes)} compromisos en total.[/dim]")


@app.command()
def contexto(
    remitente: str = typer.Option(..., "--remitente", "-r", help="Nombre de la persona"),
    mensaje: str = typer.Option("", "--mensaje", "-m", help="Mensaje de contexto para búsqueda semántica"),
) -> None:
    """Muestra el contexto completo sobre una persona sin generar respuesta."""
    from keel.storage.local import cargar_perfil, cargar_persona
    from keel.engine.respuesta import construir_prompt
    from keel.engine.presencia import analizar_tono

    try:
        perfil = cargar_perfil()
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    persona = cargar_persona(remitente)

    embedder = None
    if mensaje:
        try:
            embedder = _embedder()
        except Exception:
            pass

    texto_referencia = mensaje or "contexto general"
    tono = analizar_tono(texto_referencia) if mensaje else None
    tono_resumen = tono.resumen if tono else "—"

    ctx = construir_prompt(perfil, persona, texto_referencia, tono_resumen, embedder)

    console.print(
        Panel(
            ctx,
            title=f"[bold]Contexto sobre {remitente}[/bold]",
            border_style="cyan",
        )
    )


@app.command()
def update() -> None:
    """Actualiza keel-core a la última versión desde git."""
    import subprocess
    from pathlib import Path

    app_dir = Path.home() / ".local" / "share" / "keel-core"
    if not app_dir.exists():
        console.print("[red]Instalación no encontrada en ~/.local/share/keel-core/[/red]")
        console.print("[dim]Instala con: bash install.sh[/dim]")
        raise typer.Exit(1)

    if not (app_dir / ".git").exists():
        console.print("[yellow]La instalación no tiene git — actualización manual necesaria.[/yellow]")
        raise typer.Exit(1)

    console.print("[dim]Actualizando desde git...[/dim]")
    result = subprocess.run(
        ["git", "pull", "--ff-only"],
        cwd=app_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        console.print(f"[red]git pull falló:\n{result.stderr}[/red]")
        raise typer.Exit(1)

    console.print(f"[dim]{result.stdout.strip()}[/dim]")

    console.print("[dim]Reinstalando dependencias...[/dim]")
    pip = app_dir / ".venv" / "bin" / "pip"
    subprocess.run([str(pip), "install", "-e", ".", "--quiet"], cwd=app_dir, check=True)

    console.print("[green]✓ keel-core actualizado.[/green]")
    subprocess.run([str(app_dir / ".venv" / "bin" / "keel"), "status"])


@app.command(name="mcp")
def mcp_serve(
    transport: str = typer.Option("stdio", "--transport", "-t", help="stdio | sse"),
) -> None:
    """Inicia el servidor MCP (stdio para Claude Code, sse para otros clientes)."""
    from keel.mcp.server import mcp as mcp_server
    mcp_server.run(transport=transport)


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Dirección de escucha"),
    port: int = typer.Option(7331, "--port", "-p", help="Puerto"),
    reload: bool = typer.Option(False, "--reload", help="Hot-reload (solo desarrollo)"),
) -> None:
    """Inicia el servidor REST de keel-core en localhost:7331."""
    import uvicorn
    console.print(f"\n[bold]keel-core API[/bold] → http://{host}:{port}")
    console.print(f"[dim]Documentación: http://{host}:{port}/docs[/dim]\n")
    uvicorn.run(
        "keel.api.app:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    app()
