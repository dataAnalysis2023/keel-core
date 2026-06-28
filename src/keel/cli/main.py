"""CLI de keel."""

import json
import re
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from keel.cli import persona as persona_cli
from keel.cli import perfil as perfil_cli
from keel.cli import agenda as agenda_cli
from keel.cli import config_cli
from keel.cli import notas_cli
from keel.cli import alias_cli

app = typer.Typer(
    name="keel",
    help="Motor de extensión cognitiva personal.",
    add_completion=False,
)
app.add_typer(persona_cli.app, name="persona")
app.add_typer(perfil_cli.app, name="perfil")
app.add_typer(agenda_cli.app, name="agenda")
app.add_typer(config_cli.app, name="config")
app.add_typer(notas_cli.app, name="notas")
app.add_typer(alias_cli.app, name="alias")

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
    from keel.llm.factory import crear_llm
    from keel.models.persona import ConversacionResumen
    from keel.storage.vectorial import indexar_conversacion
    from datetime import date

    try:
        perfil = cargar_perfil()
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    persona = cargar_persona(remitente)
    llm = crear_llm(cargar_config(), modelo_override=modelo or None)

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
    console.print("[dim]Edítalo antes de usar `keel conversar`.[/dim]")


@app.command()
def status() -> None:
    """Muestra el estado completo del sistema: versión, LLM, datos, config, storage."""
    from keel.llm.factory import crear_llm
    from keel.storage.vectorial import total_indexados
    from keel.storage.local import cargar_config, keel_dir as _keel_dir
    from keel.models.persona import Persona
    from rich.table import Table
    from rich.rule import Rule
    import importlib.metadata

    directorio = _keel_dir()

    # Versión
    try:
        version = importlib.metadata.version("keel-core")
    except importlib.metadata.PackageNotFoundError:
        version = "dev"

    # LLM — siempre mostramos Ollama para referencia + proveedor activo
    from keel.llm.ollama import OllamaLLM as _OllamaLLM
    _ollama = _OllamaLLM()
    ollama_ok = _ollama.disponible()
    modelos = _ollama.modelos_disponibles() if ollama_ok else []

    # Perfil
    perfil_ok = (directorio / "perfil.json").exists()
    perfil_nombre = ""
    if perfil_ok:
        try:
            from keel.storage.local import cargar_perfil
            perfil_nombre = f" ({cargar_perfil().nombre})"
        except Exception:
            pass

    # Personas y última actividad
    personas_dir = directorio / "personas"
    archivos = sorted(personas_dir.glob("*.json")) if personas_dir.exists() else []
    n_personas = len(archivos)
    ultima_actividad = ""
    total_conversaciones = 0
    total_promesas = 0
    if archivos:
        fechas = []
        for a in archivos:
            try:
                p = Persona.model_validate_json(a.read_text())
                total_conversaciones += len(p.historial_conversaciones)
                total_promesas += len(p.promesas_pendientes)
                if p.ultima_interaccion:
                    fechas.append(p.ultima_interaccion)
            except Exception:
                pass
        ultima_actividad = max(fechas) if fechas else ""

    # Vectores
    indexados = total_indexados()

    # Config
    cfg = cargar_config()

    # Storage
    tamanio_bytes = sum(f.stat().st_size for f in directorio.rglob("*") if f.is_file()) if directorio.exists() else 0
    tamanio_str = f"{tamanio_bytes / 1024:.0f} KB" if tamanio_bytes < 1_048_576 else f"{tamanio_bytes / 1_048_576:.1f} MB"

    # Cifrado
    cifrado_activo = (directorio / ".cifrado").exists()

    console.print()
    console.print(Rule(f"[bold]keel-core v{version}[/bold]"))
    console.print()

    tabla = Table(show_header=False, box=None, padding=(0, 2))
    tabla.add_column("", style="dim", width=20)
    tabla.add_column("")

    # Sistema
    ollama_str = "[green]✓ disponible[/green]" if ollama_ok else "[red]✗ no disponible[/red]"
    if ollama_ok and modelos:
        modelo_cfg = cfg.modelo_ollama or modelos[0]
        ollama_str += f"  [dim]{modelo_cfg}[/dim]"
    tabla.add_row("Ollama", ollama_str)

    proveedor_activo = cfg.proveedor
    if proveedor_activo != "ollama":
        from keel.security.api_keys import obtener_api_key
        key = obtener_api_key(proveedor_activo)
        key_str = "[green]✓ API key configurada[/green]" if key else "[red]✗ API key faltante[/red]"
        modelo_cloud = cfg.modelo_cloud or "[dim](default)[/dim]"
        tabla.add_row(f"Proveedor ({proveedor_activo})", f"{key_str}  {modelo_cloud}")
    else:
        tabla.add_row("Proveedor activo", "[dim]ollama (local)[/dim]")

    perfil_str = f"[green]✓ configurado{perfil_nombre}[/green]" if perfil_ok else "[yellow]⚠ ejecuta: keel init[/yellow]"
    tabla.add_row("Perfil", perfil_str)

    tabla.add_row("Personas", f"{n_personas}" + (f"  [dim]última actividad: {ultima_actividad}[/dim]" if ultima_actividad else ""))
    tabla.add_row("Conversaciones", f"{total_conversaciones}  [dim]({indexados} indexadas en LanceDB)[/dim]")
    tabla.add_row("Promesas pendientes", str(total_promesas))

    # Config
    tabla.add_row("", "")
    vault_str = cfg.vault_obsidian or "[dim](~/Proyectos)[/dim]"
    tabla.add_row("Vault Obsidian", vault_str)
    tabla.add_row("Días promesa", str(cfg.dias_promesa))
    tabla.add_row("Días silencio", str(cfg.dias_silencio))

    # Seguridad y storage
    tabla.add_row("", "")
    cifrado_str = "[green]✓ activo (AES-256-GCM)[/green]" if cifrado_activo else "[dim]inactivo[/dim]"
    tabla.add_row("Cifrado", cifrado_str)
    tabla.add_row("Storage (~/.keel/)", tamanio_str)

    console.print(tabla)

    if ollama_ok and modelos:
        console.print(f"\n[dim]Modelos disponibles: {', '.join(modelos)}[/dim]")
    elif not ollama_ok:
        console.print("\n[dim]→ Para activar Ollama: ollama serve[/dim]")

    console.print()


@app.command()
def conversar(
    remitente: str = typer.Option(None, "--remitente", "-r", help="Nombre del remitente (picker si se omite)"),
    mensaje: str = typer.Argument(default="", help="Mensaje (opcional — stdin si no se da)"),
    modelo: str = typer.Option(None, "--modelo", "-m", help="Modelo Ollama"),
    sin_vectores: bool = typer.Option(False, "--sin-vectores"),
    no_editar: bool = typer.Option(False, "--no-editar", help="Omite el paso de edición en $EDITOR"),
    no_guardar: bool = typer.Option(False, "--no-guardar"),
    obsidian: bool = typer.Option(False, "--obsidian", help="Agrega el resumen al diario de Obsidian"),
    vault: str = typer.Option(None, "--vault", help="Ruta al vault de Obsidian"),
) -> None:
    """Flujo interactivo completo: mensaje → sugerencia → edición → guardado."""
    from keel.storage.local import cargar_perfil, cargar_persona, keel_dir, cargar_config
    from keel.engine.sesion import ejecutar, guardar, abrir_en_editor, leer_mensaje_stdin, generar_resumen_automatico
    from keel.llm.factory import crear_llm
    from keel.cli.utils import seleccionar_remitente
    from rich.prompt import Prompt, Confirm
    from rich.rule import Rule

    cfg = cargar_config()
    if vault is None and cfg.vault_obsidian:
        vault = cfg.vault_obsidian
    if modelo is None and cfg.modelo_ollama:
        modelo = cfg.modelo_ollama

    if not remitente:
        remitente = seleccionar_remitente(console, keel_dir())

    # ── 1. Cargar perfil ──────────────────────────────────────────────────────
    try:
        perfil = cargar_perfil()
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    persona = cargar_persona(remitente)
    llm = crear_llm(cargar_config(), modelo_override=modelo or None)

    if not llm.disponible():
        console.print("[red]Ollama no disponible. Ejecuta: ollama serve[/red]")
        raise typer.Exit(1)

    embedder = None
    if not sin_vectores:
        try:
            embedder = _embedder()
        except Exception:
            pass

    # ── 2. Obtener mensaje ────────────────────────────────────────────────────
    if not mensaje:
        if not no_editar:
            console.print(f"\n[dim]Escribe el mensaje de {remitente} (Enter×2 o Ctrl+D para terminar):[/dim]")
        mensaje = leer_mensaje_stdin()

    if not mensaje:
        console.print("[red]Mensaje vacío. Cancela.[/red]")
        raise typer.Exit(1)

    # ── 3. Mostrar contexto ──────────────────────────────────────────────────
    console.print()
    console.print(Rule(f"[dim]Conversación con {remitente}[/dim]"))

    if persona.historial_conversaciones or persona.promesas_pendientes:
        detalles = []
        if persona.historial_conversaciones:
            detalles.append(f"{len(persona.historial_conversaciones)} conversación(es) registrada(s)")
        if persona.promesas_pendientes:
            detalles.append(f"{len(persona.promesas_pendientes)} promesa(s) pendiente(s)")
        console.print(f"[dim]  {persona.nombre}: {' · '.join(detalles)}[/dim]")

    # ── 4. Generar sugerencia ─────────────────────────────────────────────────
    console.print(f"\n[dim]Tono detectado: {__import__('keel.engine.presencia', fromlist=['analizar_tono']).analizar_tono(mensaje).resumen}[/dim]")
    modo = "semántico" if embedder else ("cronológico" if persona.historial_conversaciones else "sin historial")
    console.print(f"[dim]Contexto: {modo} | Generando...[/dim]\n")

    resultado = ejecutar(perfil, persona, mensaje, llm, embedder)

    console.print(
        Panel(
            resultado.sugerencia,
            title=f"[bold]Sugerencia para {remitente}[/bold]",
            border_style="blue",
        )
    )

    # ── 5. Edición en $EDITOR ─────────────────────────────────────────────────
    texto_final = resultado.sugerencia
    if not no_editar:
        editar = Confirm.ask("\n¿Editar en $EDITOR?", default=False)
        if editar:
            texto_final = abrir_en_editor(resultado.sugerencia)
            if texto_final != resultado.sugerencia:
                console.print(
                    Panel(texto_final, title="[bold]Texto editado[/bold]", border_style="green")
                )

    # ── 6. Guardar ────────────────────────────────────────────────────────────
    if no_guardar:
        return

    guardar_sesion = Confirm.ask("\n¿Guardar esta conversación?", default=True)
    if not guardar_sesion:
        return

    resumen_auto = generar_resumen_automatico(mensaje, texto_final)
    resumen = Prompt.ask("Resumen para el historial", default=resumen_auto)
    temas_raw = Prompt.ask("Temas (separados por coma, opcional)", default="")
    temas = [t.strip() for t in temas_raw.split(",") if t.strip()]

    guardar(persona, resumen, temas, embedder)
    console.print(f"[green]✓ Guardado en el historial de {remitente}.[/green]\n")

    if obsidian:
        from keel.io.obsidian import agregar_a_diario
        from datetime import date
        entrada = f"## {date.today().isoformat()} — {remitente}\n{resumen}"
        ruta = agregar_a_diario(entrada, vault=vault)
        console.print(f"[green]✓ Entrada agregada al diario: {ruta}[/green]")




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


@app.command(name="exportar-obsidian")
def exportar_obsidian(
    remitente: str = typer.Option(None, "--remitente", "-r", help="Exportar solo esta persona"),
    vault: str = typer.Option(None, "--vault", help="Ruta al vault (default: ~/Proyectos)"),
) -> None:
    """Exporta personas como notas Obsidian con frontmatter YAML."""
    from keel.storage.local import keel_dir
    from keel.models.persona import Persona
    from keel.io.obsidian import exportar_persona

    personas_dir = keel_dir() / "personas"
    if remitente:
        archivos = [personas_dir / f"{remitente.lower()}.json"]
        archivos = [a for a in archivos if a.exists()]
    else:
        archivos = sorted(personas_dir.glob("*.json")) if personas_dir.exists() else []

    if not archivos:
        console.print("[yellow]No se encontraron personas para exportar.[/yellow]")
        raise typer.Exit(1)

    exportadas = 0
    for archivo in archivos:
        p = Persona.model_validate_json(archivo.read_text())
        ruta = exportar_persona(p, vault=vault)
        console.print(f"[green]✓[/green] [dim]{ruta}[/dim]")
        exportadas += 1

    console.print(f"\n[green]{exportadas} persona(s) exportada(s) al vault de Obsidian.[/green]")


@app.command()
def export(
    remitente: str = typer.Option(None, "--remitente", "-r", help="Exportar solo esta persona"),
    output: str = typer.Option(None, "--output", "-o", help="Archivo de salida (por defecto: stdout)"),
) -> None:
    """Exporta el contexto de personas como Markdown. Útil para pasarlo a otro LLM."""
    from keel.storage.local import keel_dir, cargar_perfil
    from keel.models.persona import Persona
    from datetime import date

    try:
        perfil = cargar_perfil()
    except FileNotFoundError:
        perfil = None

    personas_dir = keel_dir() / "personas"
    if remitente:
        archivos = [personas_dir / f"{remitente.lower()}.json"]
        archivos = [a for a in archivos if a.exists()]
    else:
        archivos = sorted(personas_dir.glob("*.json")) if personas_dir.exists() else []

    if not archivos:
        console.print("[yellow]No se encontraron personas para exportar.[/yellow]")
        raise typer.Exit(1)

    lineas: list[str] = [f"# Contexto Keel — {date.today().isoformat()}\n"]

    if perfil:
        lineas.append("## Perfil del usuario\n")
        lineas.append(f"- **Nombre**: {perfil.nombre}")
        if perfil.voz.tono:
            lineas.append(f"- **Tono**: {perfil.voz.tono}")
        if perfil.valores:
            lineas.append(f"- **Valores**: {', '.join(perfil.valores)}")
        lineas.append("")

    for archivo in archivos:
        p = Persona.model_validate_json(archivo.read_text())
        lineas.append(f"## {p.nombre}\n")
        if p.rol:
            lineas.append(f"- **Rol**: {p.rol}")
        if p.como_nos_conocemos:
            lineas.append(f"- **Cómo nos conocemos**: {p.como_nos_conocemos}")
        if p.tono_relacional:
            lineas.append(f"- **Tono relacional**: {p.tono_relacional}")
        if p.sensibilidades:
            lineas.append(f"- **Sensibilidades**: {', '.join(p.sensibilidades)}")
        if p.estado_actual:
            lineas.append(f"- **Estado actual**: {p.estado_actual}")
        if p.ultima_interaccion:
            lineas.append(f"- **Última interacción**: {p.ultima_interaccion}")

        if p.historial_conversaciones:
            lineas.append("\n### Conversaciones recientes")
            for conv in p.historial_conversaciones[-5:]:
                temas = f" [{', '.join(conv.temas)}]" if conv.temas else ""
                lineas.append(f"- `{conv.fecha}`{temas}: {conv.resumen}")

        if p.promesas_pendientes:
            lineas.append("\n### Compromisos pendientes")
            for pr in p.promesas_pendientes:
                fecha = f" (hasta {pr.fecha_compromiso})" if pr.fecha_compromiso else ""
                lineas.append(f"- {pr.descripcion}{fecha}")

        lineas.append("")

    contenido = "\n".join(lineas)

    if output:
        Path(output).write_text(contenido, encoding="utf-8")
        console.print(f"[green]✓ Exportado en {output}[/green]")
    else:
        console.print(contenido)


@app.command()
def volcar(
    persona: str = typer.Option(None, "--persona", "-p", help="Exportar solo esta persona"),
    recientes: int = typer.Option(3, "--recientes", "-n", help="Conversaciones recientes por persona"),
    sin_framing: bool = typer.Option(False, "--sin-framing", help="Omite el encabezado de instrucción para el LLM"),
    sin_notas: bool = typer.Option(False, "--sin-notas", help="Omite la sección de notas personales"),
    notas_top: int = typer.Option(5, "--notas-top", help="Número de notas recientes a incluir"),
    al_clipboard: bool = typer.Option(False, "--clipboard", help="Copia al portapapeles"),
    output: str = typer.Option(None, "--output", "-o", help="Archivo de salida (por defecto: stdout)"),
) -> None:
    """Vuelca todo el contexto como Markdown optimizado para pegar en Claude.ai u otro LLM."""
    from keel.storage.local import cargar_perfil, cargar_persona, keel_dir, cargar_notas
    from keel.models.persona import Persona
    from keel.engine.volcado import volcar_a_markdown

    try:
        perfil = cargar_perfil()
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    if persona:
        personas = [cargar_persona(persona)]
        notas = []
    else:
        personas_dir = keel_dir() / "personas"
        archivos = sorted(personas_dir.glob("*.json")) if personas_dir.exists() else []
        personas = [Persona.model_validate_json(a.read_text()) for a in archivos]
        notas = [] if sin_notas else cargar_notas()

    if not personas and not notas:
        console.print("[yellow]No hay personas ni notas registradas.[/yellow]")
        raise typer.Exit(0)

    contenido = volcar_a_markdown(
        perfil, personas,
        recientes=recientes,
        con_framing=not sin_framing,
        notas=notas or None,
        notas_top=notas_top,
    )

    if output:
        Path(output).write_text(contenido, encoding="utf-8")
        console.print(f"[green]✓ Volcado guardado en {output}[/green]")
    elif al_clipboard:
        try:
            from keel.io.clipboard import escribir as escribir_clipboard
            escribir_clipboard(contenido)
            n_personas = len(personas)
            n_convs = sum(len(p.historial_conversaciones) for p in personas)
            console.print(
                f"[green]✓ Contexto copiado al portapapeles "
                f"({n_personas} persona(s) · {n_convs} conversación(es)).[/green]"
            )
        except RuntimeError as e:
            console.print(f"[yellow]{e}[/yellow]")
    else:
        console.print(contenido)


@app.command()
def clip(
    remitente: str = typer.Option(None, "--remitente", "-r", help="Nombre del remitente (picker si se omite)"),
    modelo: str = typer.Option(None, "--modelo", "-m", help="Modelo Ollama"),
    sin_vectores: bool = typer.Option(False, "--sin-vectores"),
    no_guardar: bool = typer.Option(False, "--no-guardar"),
    copiar: bool = typer.Option(False, "--copiar", "-c", help="Copia la sugerencia al clipboard sin preguntar"),
) -> None:
    """Lee el mensaje del clipboard, genera una sugerencia y opcionalmente la devuelve al clipboard."""
    from keel.io.clipboard import leer as leer_clipboard, escribir as escribir_clipboard
    from keel.storage.local import cargar_perfil, cargar_persona, keel_dir, cargar_config
    from keel.engine.sesion import ejecutar, guardar, generar_resumen_automatico
    from keel.llm.factory import crear_llm
    from keel.cli.utils import seleccionar_remitente
    from rich.prompt import Confirm, Prompt
    from rich.rule import Rule

    cfg = cargar_config()
    if not no_guardar and cfg.clipboard_no_guardar:
        no_guardar = True
    if modelo is None and cfg.modelo_ollama:
        modelo = cfg.modelo_ollama

    # ── 1. Leer clipboard ─────────────────────────────────────────────────────
    try:
        mensaje = leer_clipboard()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    if not remitente:
        remitente = seleccionar_remitente(console, keel_dir())

    console.print()
    console.print(Rule(f"[dim]Mensaje de {remitente} (clipboard)[/dim]"))
    console.print(
        Panel(mensaje.strip(), title="[dim]Contenido leído[/dim]", border_style="dim")
    )

    if not Confirm.ask("¿Procesar este mensaje?", default=True):
        console.print("[dim]Cancelado.[/dim]")
        raise typer.Exit(0)

    # ── 2. Cargar contexto ────────────────────────────────────────────────────
    try:
        perfil = cargar_perfil()
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    persona = cargar_persona(remitente)
    llm = crear_llm(cargar_config(), modelo_override=modelo or None)

    if not llm.disponible():
        console.print("[red]Ollama no disponible. Ejecuta: ollama serve[/red]")
        raise typer.Exit(1)

    embedder = None
    if not sin_vectores:
        try:
            embedder = _embedder()
        except Exception:
            pass

    # ── 3. Generar sugerencia ─────────────────────────────────────────────────
    modo = "semántico" if embedder else ("cronológico" if persona.historial_conversaciones else "sin historial")
    console.print(f"\n[dim]Contexto: {modo} | Generando...[/dim]\n")

    resultado = ejecutar(perfil, persona, mensaje, llm, embedder)

    console.print(
        Panel(
            resultado.sugerencia,
            title=f"[bold]Sugerencia para {remitente}[/bold]",
            border_style="blue",
        )
    )

    # ── 4. Copiar al clipboard ────────────────────────────────────────────────
    if copiar or Confirm.ask("\n¿Copiar sugerencia al clipboard?", default=True):
        try:
            escribir_clipboard(resultado.sugerencia)
            console.print("[green]✓ Sugerencia copiada al clipboard.[/green]")
        except RuntimeError as e:
            console.print(f"[yellow]No se pudo copiar: {e}[/yellow]")

    # ── 5. Guardar ────────────────────────────────────────────────────────────
    if no_guardar:
        return

    if Confirm.ask("\n¿Guardar esta conversación en el historial?", default=True):
        resumen_auto = generar_resumen_automatico(mensaje, resultado.sugerencia)
        resumen = Prompt.ask("Resumen para el historial", default=resumen_auto)
        temas_raw = Prompt.ask("Temas (separados por coma, opcional)", default="")
        temas = [t.strip() for t in temas_raw.split(",") if t.strip()]
        guardar(persona, resumen, temas, embedder)
        console.print(f"[green]✓ Guardado en el historial de {remitente}.[/green]\n")


@app.command()
def importar(
    archivo: str = typer.Argument(..., help="Ruta al archivo a importar"),
    persona: str = typer.Option(..., "--persona", "-p", help="Nombre de la persona"),
    formato: str = typer.Option("auto", "--formato", "-f", help="whatsapp | texto | csv | auto"),
    agrupar: bool = typer.Option(True, "--agrupar/--sin-agrupar", help="Agrupa mensajes por día"),
    no_vectores: bool = typer.Option(False, "--sin-vectores"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Muestra qué importaría sin guardar"),
) -> None:
    """Importa historial de conversaciones desde WhatsApp, texto plano o CSV."""
    from keel.io.fuentes import detectar_fuente, fuente_para_formato
    from keel.storage.local import cargar_persona, guardar_persona
    from keel.storage.vectorial import indexar_conversacion
    from keel.models.persona import ConversacionResumen
    from datetime import date
    from pathlib import Path
    from rich.table import Table

    ruta = Path(archivo)
    if not ruta.exists():
        console.print(f"[red]Archivo no encontrado: {archivo}[/red]")
        raise typer.Exit(1)

    contenido = ruta.read_text(encoding="utf-8", errors="replace")
    hoy = date.today().isoformat()

    # Instanciar la fuente correcta
    if formato == "auto":
        fuente = detectar_fuente(contenido, ruta.suffix.lower(), fecha_defecto=hoy)
    else:
        fuente = fuente_para_formato(formato, fecha_defecto=hoy)

    mensajes = fuente.leer(contenido)

    if agrupar:
        resumenes = fuente.agrupar(mensajes, persona)
    else:
        resumenes = [
            {"fecha": m.fecha, "resumen": m.texto[:120], "temas": []}
            for m in mensajes if m.remitente.lower() == persona.lower()
        ]

    if not resumenes:
        console.print(f"[yellow]No se encontraron mensajes de '{persona}' en el archivo.[/yellow]")
        raise typer.Exit(0)

    # Preview
    tabla = Table(title=f"Vista previa — {len(resumenes)} entrada(s) a importar", show_lines=True)
    tabla.add_column("Fecha", style="dim", width=12)
    tabla.add_column("Resumen")
    for r in resumenes[:10]:
        tabla.add_row(r["fecha"], r["resumen"])
    if len(resumenes) > 10:
        tabla.add_row("...", f"y {len(resumenes) - 10} más")
    console.print(tabla)

    if dry_run:
        console.print("[dim]--dry-run activo: no se guardó nada.[/dim]")
        raise typer.Exit(0)

    if not Confirm.ask(f"\n¿Importar {len(resumenes)} entrada(s) al historial de {persona}?", default=True):
        console.print("[dim]Cancelado.[/dim]")
        raise typer.Exit(0)

    p = cargar_persona(persona)
    fechas_existentes = {c.fecha for c in p.historial_conversaciones}
    embedder = None
    if not no_vectores:
        try:
            embedder = _embedder()
        except Exception:
            pass

    nuevos = 0
    for r in resumenes:
        if r["fecha"] in fechas_existentes:
            continue
        p.historial_conversaciones.append(
            ConversacionResumen(fecha=r["fecha"], resumen=r["resumen"], temas=r["temas"])
        )
        fechas_existentes.add(r["fecha"])
        if embedder:
            try:
                indexar_conversacion(persona, r["fecha"], r["resumen"], r["temas"], embedder)
            except Exception:
                pass
        nuevos += 1

    p.historial_conversaciones.sort(key=lambda c: c.fecha)
    guardar_persona(p)

    console.print(f"[green]✓ {nuevos} entrada(s) importadas en el historial de {persona}.[/green]")
    if embedder:
        console.print(f"[dim]Indexadas en LanceDB.[/dim]")


@app.command()
def historial(
    persona: str = typer.Option(..., "--persona", "-p", help="Nombre de la persona"),
    desde: str = typer.Option(None, "--desde", help="Fecha inicio YYYY-MM-DD (inclusive)"),
    hasta: str = typer.Option(None, "--hasta", help="Fecha fin YYYY-MM-DD (inclusive)"),
    top: int = typer.Option(None, "--top", "-n", help="Mostrar solo los N más recientes"),
    as_json: bool = typer.Option(False, "--json", help="Salida en JSON"),
) -> None:
    """Muestra el historial cronológico de conversaciones con una persona."""
    from keel.storage.local import cargar_persona
    from rich.table import Table

    p = cargar_persona(persona)

    if not p.historial_conversaciones:
        console.print(f"[yellow]No hay historial para '{persona}'.[/yellow]")
        raise typer.Exit(0)

    entradas = sorted(p.historial_conversaciones, key=lambda c: c.fecha)

    if desde:
        entradas = [c for c in entradas if c.fecha >= desde]
    if hasta:
        entradas = [c for c in entradas if c.fecha <= hasta]

    if top:
        entradas = entradas[-top:]

    if not entradas:
        console.print(f"[yellow]Sin conversaciones en ese rango para '{persona}'.[/yellow]")
        raise typer.Exit(0)

    if as_json:
        import json as _json
        console.print(_json.dumps([c.model_dump() for c in entradas], ensure_ascii=False, indent=2))
        return

    tabla = Table(
        title=f"Historial de {persona} — {len(entradas)} entrada(s)",
        show_lines=True,
    )
    tabla.add_column("Fecha", style="dim", width=12)
    tabla.add_column("Resumen")
    tabla.add_column("Temas", style="dim", width=22)

    for c in entradas:
        tabla.add_row(c.fecha, c.resumen, ", ".join(c.temas) if c.temas else "—")

    console.print()
    console.print(tabla)
    if p.ultima_interaccion:
        console.print(f"\n[dim]Última interacción registrada: {p.ultima_interaccion}[/dim]")


@app.command()
def stats(
    as_json: bool = typer.Option(False, "--json", help="Salida en JSON"),
) -> None:
    """Muestra estadísticas del grafo relacional: personas, conversaciones, temas, agenda."""
    from keel.storage.local import keel_dir
    from keel.models.persona import Persona
    from keel.engine.stats import calcular_stats
    from rich.table import Table
    from rich.rule import Rule
    import json as _json

    personas_dir = keel_dir() / "personas"
    archivos = sorted(personas_dir.glob("*.json")) if personas_dir.exists() else []
    personas = [Persona.model_validate_json(a.read_text()) for a in archivos]

    if not personas:
        console.print("[yellow]No hay personas registradas.[/yellow]")
        raise typer.Exit(0)

    s = calcular_stats(personas)

    if as_json:
        console.print(_json.dumps(s, ensure_ascii=False, indent=2))
        return

    console.print()
    console.print(Rule("[bold]Estadísticas del grafo relacional[/bold]"))
    console.print()

    # Resumen global
    console.print(f"  Personas registradas:      [bold]{s['total_personas']}[/bold]")
    console.print(f"  Conversaciones totales:    [bold]{s['total_conversaciones']}[/bold]")
    console.print(f"  Promesas pendientes:       [bold]{s['total_promesas_pendientes']}[/bold]")
    if s["promesas_vencidas"]:
        console.print(f"  Promesas vencidas:         [bold red]{len(s['promesas_vencidas'])}[/bold red]")
    if s["sin_historial"]:
        console.print(f"  Sin historial:             [dim]{', '.join(s['sin_historial'])}[/dim]")
    console.print()

    # Personas más activas
    if s["personas_activas"]:
        tabla = Table(title="Personas más activas", show_header=True, box=None, padding=(0, 2))
        tabla.add_column("Persona", style="bold cyan")
        tabla.add_column("Conversaciones", justify="right")
        tabla.add_column("Última interacción", style="dim")
        for d in s["personas_activas"]:
            tabla.add_row(d["nombre"], str(d["conversaciones"]), d["ultima"])
        console.print(tabla)
        console.print()

    # Temas frecuentes
    if s["temas_frecuentes"]:
        temas_str = "  ".join(f"[cyan]{d['tema']}[/cyan] [dim]×{d['menciones']}[/dim]" for d in s["temas_frecuentes"][:8])
        console.print(f"[bold]Temas frecuentes:[/bold]  {temas_str}")
        console.print()

    # Distribución temporal (últimos 6 meses)
    por_mes = s["conversaciones_por_mes"]
    if por_mes:
        meses = list(por_mes.items())[-6:]
        max_val = max(v for _, v in meses) if meses else 1
        console.print("[bold]Actividad mensual:[/bold]")
        for mes, n in meses:
            barra = "█" * int(n / max_val * 20)
            console.print(f"  {mes}  [green]{barra:<20}[/green]  {n}")
        console.print()

    # Promesas vencidas
    if s["promesas_vencidas"]:
        tabla = Table(title="[red]Promesas vencidas[/red]", show_header=True, box=None, padding=(0, 2))
        tabla.add_column("Persona", style="bold")
        tabla.add_column("Descripción")
        tabla.add_column("Vencida hace", style="red", justify="right")
        for d in s["promesas_vencidas"]:
            tabla.add_row(d["persona"], d["descripcion"], f"{d['dias_vencida']}d")
        console.print(tabla)
        console.print()


@app.command()
def buscar(
    texto: str = typer.Argument(..., help="Texto o tema a buscar"),
    persona: str = typer.Option(None, "--persona", "-p", help="Filtrar por persona"),
    top: int = typer.Option(5, "--top", "-n", help="Número de resultados"),
    sin_vectores: bool = typer.Option(False, "--sin-vectores", help="Fuerza búsqueda por keyword"),
    desde: str = typer.Option(None, "--desde", help="Fecha inicio YYYY-MM-DD (inclusive)"),
    hasta: str = typer.Option(None, "--hasta", help="Fecha fin YYYY-MM-DD (inclusive)"),
) -> None:
    """Busca en el historial de conversaciones por tema o texto, con filtros opcionales de fecha."""
    from keel.storage.local import keel_dir
    from keel.models.persona import Persona
    from keel.engine.busqueda import buscar_global
    from rich.table import Table

    for etiqueta, valor in [("--desde", desde), ("--hasta", hasta)]:
        if valor:
            try:
                __import__("datetime").date.fromisoformat(valor)
            except ValueError:
                console.print(f"[red]Fecha inválida en {etiqueta}: '{valor}'. Usa YYYY-MM-DD.[/red]")
                raise typer.Exit(1)

    personas_dir = keel_dir() / "personas"
    archivos = sorted(personas_dir.glob("*.json")) if personas_dir.exists() else []
    personas_lista = [Persona.model_validate_json(a.read_text()) for a in archivos]

    if not personas_lista:
        console.print("[yellow]No hay personas registradas.[/yellow]")
        raise typer.Exit(0)

    embedder = None
    if not sin_vectores:
        try:
            embedder = _embedder()
        except Exception:
            pass

    resultados = buscar_global(
        texto, personas_lista, embedder,
        top=top, filtro_persona=persona,
        desde=desde, hasta=hasta,
    )

    if not resultados:
        console.print(f"[yellow]Sin resultados para '[bold]{texto}[/bold]'.[/yellow]")
        raise typer.Exit(0)

    modo = resultados[0].get("modo", "keyword")
    tabla = Table(
        title=f"Resultados para '{texto}' — modo {modo}",
        show_lines=True,
    )
    tabla.add_column("Persona", style="bold", width=12)
    tabla.add_column("Fecha", style="dim", width=12)
    tabla.add_column("Resumen")
    tabla.add_column("Temas", style="dim", width=20)

    for r in resultados:
        tabla.add_row(r["persona"], r["fecha"], r["resumen"], r.get("temas", ""))

    console.print(tabla)
    console.print(f"\n[dim]{len(resultados)} resultado(s).[/dim]")


@app.command()
def hoy(
    fecha: str = typer.Option(None, "--fecha", help="Fecha a revisar YYYY-MM-DD (default: hoy)"),
    al_clipboard: bool = typer.Option(False, "--clipboard", help="Copia el resumen al clipboard"),
    obsidian: bool = typer.Option(False, "--obsidian", help="Agrega el resumen al diario de Obsidian"),
    vault: str = typer.Option(None, "--vault", help="Ruta al vault de Obsidian"),
) -> None:
    """Muestra un resumen de la actividad del día: conversaciones, promesas, personas."""
    from keel.storage.local import keel_dir, cargar_config
    from keel.models.persona import Persona
    from datetime import date
    from rich.rule import Rule
    from rich.table import Table

    cfg = cargar_config()
    if vault is None and cfg.vault_obsidian:
        vault = cfg.vault_obsidian

    dia = fecha or date.today().isoformat()

    try:
        date.fromisoformat(dia)
    except ValueError:
        console.print(f"[red]Fecha inválida: '{dia}'. Usa formato YYYY-MM-DD.[/red]")
        raise typer.Exit(1)

    personas_dir = keel_dir() / "personas"
    archivos = sorted(personas_dir.glob("*.json")) if personas_dir.exists() else []
    personas = [Persona.model_validate_json(a.read_text()) for a in archivos]

    conversaciones_hoy: list[dict] = []
    promesas_hoy: list[dict] = []

    for p in personas:
        for conv in p.historial_conversaciones:
            if conv.fecha == dia:
                conversaciones_hoy.append({
                    "persona": p.nombre,
                    "resumen": conv.resumen,
                    "temas": conv.temas,
                })
        for pr in p.promesas_pendientes:
            # Detecta promesas cuya fecha_compromiso coincide con hoy
            # (proxy para "agregada hoy" — sin campo created_at)
            if pr.fecha_compromiso == dia:
                promesas_hoy.append({
                    "persona": p.nombre,
                    "descripcion": pr.descripcion,
                })

    console.print()
    console.print(Rule(f"[bold]Resumen del {dia}[/bold]"))
    console.print()

    if not conversaciones_hoy and not promesas_hoy:
        console.print(f"[dim]Sin actividad registrada para {dia}.[/dim]")
        console.print()
        return

    lineas_md: list[str] = [f"# Resumen del día — {dia}\n"]

    if conversaciones_hoy:
        tabla = Table(title=f"Conversaciones ({len(conversaciones_hoy)})", show_lines=False, box=None, padding=(0, 2))
        tabla.add_column("Con quién", style="bold cyan", width=14)
        tabla.add_column("Resumen")
        tabla.add_column("Temas", style="dim", width=20)
        for c in conversaciones_hoy:
            tabla.add_row(c["persona"], c["resumen"], ", ".join(c["temas"]) if c["temas"] else "—")
        console.print(tabla)
        console.print()

        lineas_md.append("## Conversaciones\n")
        for c in conversaciones_hoy:
            temas = f" [{', '.join(c['temas'])}]" if c["temas"] else ""
            lineas_md.append(f"- **{c['persona']}**{temas}: {c['resumen']}")
        lineas_md.append("")

    if promesas_hoy:
        tabla_pr = Table(title=f"Promesas con fecha hoy ({len(promesas_hoy)})", show_lines=False, box=None, padding=(0, 2))
        tabla_pr.add_column("Con quién", style="bold", width=14)
        tabla_pr.add_column("Compromiso")
        for pr in promesas_hoy:
            tabla_pr.add_row(pr["persona"], pr["descripcion"])
        console.print(tabla_pr)
        console.print()

        lineas_md.append("## Compromisos con fecha hoy\n")
        for pr in promesas_hoy:
            lineas_md.append(f"- **{pr['persona']}**: {pr['descripcion']}")
        lineas_md.append("")

    personas_activas = list({c["persona"] for c in conversaciones_hoy})
    console.print(f"[dim]{len(conversaciones_hoy)} conversación(es) · {len(promesas_hoy)} promesa(s) con fecha hoy · {len(personas_activas)} persona(s)[/dim]")
    console.print()

    markdown = "\n".join(lineas_md)

    if al_clipboard:
        try:
            from keel.io.clipboard import escribir as escribir_clipboard
            escribir_clipboard(markdown)
            console.print("[green]✓ Resumen copiado al clipboard.[/green]")
        except RuntimeError as e:
            console.print(f"[yellow]{e}[/yellow]")

    if obsidian:
        from keel.io.obsidian import agregar_a_diario
        ruta = agregar_a_diario(markdown, vault=vault)
        console.print(f"[green]✓ Resumen agregado al diario: {ruta}[/green]")


@app.command()
def sugerir(
    top: int = typer.Option(3, "--top", "-n", help="Número de contactos sugeridos"),
    sin_llm: bool = typer.Option(False, "--sin-llm", help="Omite la síntesis LLM"),
    modelo: str = typer.Option(None, "--modelo", "-m"),
    al_clipboard: bool = typer.Option(False, "--clipboard", help="Copia las sugerencias al clipboard"),
) -> None:
    """Sugiere quién contactar hoy y por qué, ordenado por urgencia relacional."""
    from keel.storage.local import cargar_perfil, keel_dir, cargar_config
    from keel.models.persona import Persona
    from keel.engine.sugerencias import sugerir_contactos, sugerencias_a_texto, construir_prompt_sugerencias
    from rich.rule import Rule

    cfg = cargar_config()
    if modelo is None and cfg.modelo_ollama:
        modelo = cfg.modelo_ollama

    try:
        perfil = cargar_perfil()
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    personas_dir = keel_dir() / "personas"
    archivos = sorted(personas_dir.glob("*.json")) if personas_dir.exists() else []
    personas = [Persona.model_validate_json(a.read_text()) for a in archivos]

    if not personas:
        console.print("[yellow]No hay personas registradas.[/yellow]")
        raise typer.Exit(0)

    sugerencias = sugerir_contactos(
        personas, top=top,
        dias_silencio=cfg.dias_silencio,
        dias_promesa=cfg.dias_promesa,
    )

    console.print()
    console.print(Rule("[bold]Sugerencias de contacto[/bold]"))
    console.print()

    if not sugerencias:
        console.print("[green]Sin contactos urgentes en este momento.[/green]")
        console.print()
        return

    for i, s in enumerate(sugerencias, 1):
        console.print(f"  [bold cyan]{i}. {s.persona}[/bold cyan]")
        for r in s.razones:
            console.print(f"     [dim]·[/dim] {r}")
        console.print()

    sintesis = ""
    if not sin_llm:
        from keel.llm.factory import crear_llm
        llm = crear_llm(cargar_config(), modelo_override=modelo or None)
        if llm.disponible():
            prompt = construir_prompt_sugerencias(sugerencias, perfil.nombre)
            sintesis = llm.generar(prompt)
            console.print(f"[dim]{sintesis}[/dim]")
            console.print()
        else:
            console.print("[dim]Ollama no disponible — sin síntesis.[/dim]")

    if al_clipboard:
        texto = sugerencias_a_texto(sugerencias)
        if sintesis:
            texto += f"\n\n{sintesis}"
        try:
            from keel.io.clipboard import escribir as escribir_clipboard
            escribir_clipboard(texto)
            console.print("[green]✓ Sugerencias copiadas al clipboard.[/green]")
        except RuntimeError as e:
            console.print(f"[yellow]{e}[/yellow]")


@app.command()
def pregunta(
    texto: str = typer.Argument(..., help="La pregunta"),
    persona_nombre: str = typer.Option(None, "--persona", "-p", help="Filtra a una persona (sin flag = busca en todas)"),
    top: int = typer.Option(5, "--top", "-n", help="Fragmentos de historial a usar como contexto"),
    sin_vectores: bool = typer.Option(False, "--sin-vectores"),
    sin_llm: bool = typer.Option(False, "--sin-llm", help="Muestra el historial relevante sin síntesis LLM"),
    modelo: str = typer.Option(None, "--modelo", "-m"),
    al_clipboard: bool = typer.Option(False, "--clipboard", help="Copia la respuesta al portapapeles"),
) -> None:
    """Pregunta al LLM algo usando el historial como contexto. Sin --persona, busca en todas las personas y notas."""
    from keel.storage.local import cargar_perfil, cargar_persona, keel_dir, cargar_config, cargar_notas
    from keel.models.persona import Persona
    from keel.engine.busqueda import buscar_global, buscar_notas
    from keel.engine.pregunta import construir_prompt_pregunta, respuesta_sin_llm
    from rich.rule import Rule

    cfg = cargar_config()
    if modelo is None and cfg.modelo_ollama:
        modelo = cfg.modelo_ollama

    try:
        perfil = cargar_perfil()
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    # Modo: persona específica vs. todas las personas
    if persona_nombre:
        persona_obj = cargar_persona(persona_nombre)
        personas = [persona_obj]
        titulo_rule = f"Pregunta sobre {persona_nombre}"
        notas = []
    else:
        personas_dir = keel_dir() / "personas"
        archivos = sorted(personas_dir.glob("*.json")) if personas_dir.exists() else []
        personas = [Persona.model_validate_json(a.read_text()) for a in archivos]
        persona_obj = None
        titulo_rule = "Pregunta global"
        notas = cargar_notas()
        if not personas and not notas:
            console.print("[yellow]No hay personas ni notas registradas.[/yellow]")
            raise typer.Exit(0)

    embedder = None
    if not sin_vectores:
        try:
            embedder = _embedder()
        except Exception:
            pass

    contexto = buscar_global(texto, personas, embedder=embedder, top=top)
    if notas:
        ctx_notas = buscar_notas(texto, notas, embedder=embedder, top=top)
        contexto = sorted(contexto + ctx_notas, key=lambda r: r.get("fecha", ""), reverse=True)[:top]

    console.print()
    console.print(Rule(f"[dim]{titulo_rule}[/dim]"))

    if sin_llm:
        respuesta = respuesta_sin_llm(contexto, persona_nombre)
        console.print(Panel(respuesta, title="[bold]Historial relevante[/bold]", border_style="cyan"))
    else:
        from keel.llm.factory import crear_llm
        llm = crear_llm(cargar_config(), modelo_override=modelo or None)
        if not llm.disponible():
            console.print("[yellow]Ollama no disponible — mostrando historial sin síntesis.[/yellow]")
            respuesta = respuesta_sin_llm(contexto, persona_nombre)
            console.print(Panel(respuesta, title="[bold]Historial relevante[/bold]", border_style="cyan"))
        else:
            scope = persona_nombre or f"{len(personas)} persona(s)"
            console.print(f"[dim]  {len(contexto)} fragmento(s) · {scope} | Generando...[/dim]\n")
            prompt = construir_prompt_pregunta(texto, persona_obj, perfil.nombre, contexto)
            respuesta = llm.generar(prompt)
            console.print(Panel(respuesta, title="[bold]Respuesta[/bold]", border_style="green"))

    if al_clipboard:
        try:
            from keel.io.clipboard import escribir as escribir_clipboard
            escribir_clipboard(respuesta)
            console.print("[dim]  ✓ Copiado al portapapeles.[/dim]")
        except RuntimeError as e:
            console.print(f"[yellow]{e}[/yellow]")


@app.command()
def preparar(
    persona: str = typer.Option(..., "--persona", "-p", help="Nombre de la persona"),
    recientes: int = typer.Option(5, "--recientes", "-n", help="Número de conversaciones recientes a incluir"),
    sin_llm: bool = typer.Option(False, "--sin-llm", help="Omite la síntesis LLM"),
    modelo: str = typer.Option(None, "--modelo", "-m"),
    al_clipboard: bool = typer.Option(False, "--clipboard", help="Copia el briefing al clipboard"),
    obsidian: bool = typer.Option(False, "--obsidian", help="Exporta a Obsidian"),
    vault: str = typer.Option(None, "--vault", help="Ruta al vault de Obsidian"),
) -> None:
    """Genera un briefing pre-conversación: contexto y puntos clave sobre una persona."""
    from keel.storage.local import cargar_perfil, cargar_persona, cargar_config
    from keel.engine.preparar import briefing_a_markdown, construir_prompt_briefing
    from rich.rule import Rule

    cfg = cargar_config()
    if vault is None and cfg.vault_obsidian:
        vault = cfg.vault_obsidian
    if modelo is None and cfg.modelo_ollama:
        modelo = cfg.modelo_ollama

    try:
        perfil = cargar_perfil()
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    p = cargar_persona(persona)

    sintesis = ""
    if not sin_llm:
        from keel.llm.factory import crear_llm
        llm = crear_llm(cargar_config(), modelo_override=modelo or None)
        if llm.disponible():
            console.print(f"[dim]Generando síntesis para {persona}...[/dim]")
            prompt = construir_prompt_briefing(p, perfil.nombre, n_recientes=recientes)
            sintesis = llm.generar(prompt)
        else:
            console.print("[dim]Ollama no disponible — briefing sin síntesis LLM.[/dim]")

    markdown = briefing_a_markdown(p, sintesis, n_recientes=recientes)

    console.print()
    console.print(Rule(f"[bold]Briefing — {persona}[/bold]"))
    console.print(markdown)

    if al_clipboard:
        try:
            from keel.io.clipboard import escribir as escribir_clipboard
            escribir_clipboard(markdown)
            console.print("[green]✓ Briefing copiado al clipboard.[/green]")
        except RuntimeError as e:
            console.print(f"[yellow]{e}[/yellow]")

    if obsidian:
        from keel.io.obsidian import escribir_nota
        from datetime import date
        from pathlib import Path
        vault_path = Path(vault) if vault else Path.home() / "Proyectos"
        ruta = vault_path / "keel" / "briefings" / f"{persona.lower()}-{date.today().isoformat()}.md"
        escribir_nota(ruta, markdown, frontmatter={"type": "briefing", "persona": persona, "fecha": date.today().isoformat()})
        console.print(f"[green]✓ Briefing exportado a: {ruta}[/green]")


@app.command()
def reflexionar(
    dias_promesa: int = typer.Option(None, "--dias-promesa", help="Alerta promesas que vencen en <= N días"),
    dias_silencio: int = typer.Option(None, "--dias-silencio", help="Alerta personas sin contacto en >= N días"),
    sin_llm: bool = typer.Option(False, "--sin-llm", help="Omite la síntesis LLM"),
    modelo: str = typer.Option(None, "--modelo", "-m"),
    al_clipboard: bool = typer.Option(False, "--clipboard", help="Copia el digest al clipboard"),
    output: str = typer.Option(None, "--output", "-o", help="Guarda el digest en un archivo Markdown"),
    obsidian: bool = typer.Option(False, "--obsidian", help="Escribe la reflexión en el vault de Obsidian"),
    vault: str = typer.Option(None, "--vault", help="Ruta al vault de Obsidian (default de config o ~/Proyectos)"),
) -> None:
    """Genera un digest semanal del estado de tus relaciones."""
    from keel.storage.local import cargar_perfil, keel_dir, cargar_config
    cfg = cargar_config()
    if dias_promesa is None:
        dias_promesa = cfg.dias_promesa
    if dias_silencio is None:
        dias_silencio = cfg.dias_silencio
    if vault is None and cfg.vault_obsidian:
        vault = cfg.vault_obsidian
    if modelo is None and cfg.modelo_ollama:
        modelo = cfg.modelo_ollama
    from keel.models.persona import Persona
    from keel.engine.reflexion import construir_digest, construir_sintesis, digest_a_markdown
    from rich.rule import Rule
    from pathlib import Path

    try:
        perfil = cargar_perfil()
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    personas_dir = keel_dir() / "personas"
    archivos = sorted(personas_dir.glob("*.json")) if personas_dir.exists() else []
    personas = [Persona.model_validate_json(a.read_text()) for a in archivos]

    if not personas:
        console.print("[yellow]No hay personas registradas.[/yellow]")
        raise typer.Exit(0)

    console.print(f"\n[dim]Analizando {len(personas)} persona(s)...[/dim]")
    digest = construir_digest(personas, dias_promesa=dias_promesa, dias_sin_contacto=dias_silencio)

    sintesis = ""
    if not sin_llm:
        from keel.llm.factory import crear_llm
        llm = crear_llm(cargar_config(), modelo_override=modelo or None)
        if llm.disponible():
            console.print("[dim]Generando síntesis...[/dim]")
            sintesis = construir_sintesis(digest, perfil.nombre, llm)
        else:
            console.print("[dim]Ollama no disponible — digest sin síntesis LLM.[/dim]")

    markdown = digest_a_markdown(digest, sintesis)

    console.print()
    console.print(Rule("[bold]Reflexión semanal[/bold]"))
    console.print(markdown)

    if al_clipboard:
        try:
            from keel.io.clipboard import escribir as escribir_clipboard
            escribir_clipboard(markdown)
            console.print("[green]✓ Digest copiado al clipboard.[/green]")
        except RuntimeError as e:
            console.print(f"[yellow]{e}[/yellow]")

    if output:
        Path(output).write_text(markdown, encoding="utf-8")
        console.print(f"[green]✓ Guardado en {output}[/green]")

    if obsidian:
        from keel.io.obsidian import exportar_reflexion
        ruta = exportar_reflexion(markdown, vault=vault)
        console.print(f"[green]✓ Reflexión exportada a Obsidian: {ruta}[/green]")


@app.command()
def backup(
    output: str = typer.Option(None, "--output", "-o", help="Ruta del archivo ZIP (default: ~/keel-backup-FECHA.zip)"),
) -> None:
    """Crea un backup de ~/.keel/ como archivo ZIP con fecha."""
    import zipfile
    from keel.storage.local import keel_dir
    from datetime import date

    directorio = keel_dir()
    fecha = date.today().isoformat()
    destino = Path(output) if output else Path.home() / f"keel-backup-{fecha}.zip"

    archivos = list(directorio.rglob("*"))
    archivos = [a for a in archivos if a.is_file()]

    if not archivos:
        console.print("[yellow]No hay datos en ~/.keel/ para respaldar.[/yellow]")
        raise typer.Exit(0)

    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as zf:
        for archivo in archivos:
            zf.write(archivo, archivo.relative_to(directorio.parent))

    tamanio_kb = destino.stat().st_size // 1024
    console.print(f"[green]✓ Backup creado: {destino}[/green]")
    console.print(f"[dim]{len(archivos)} archivo(s) · {tamanio_kb} KB[/dim]")


@app.command()
def restaurar(
    archivo: str = typer.Argument(..., help="Ruta al archivo ZIP de backup"),
    forzar: bool = typer.Option(False, "--forzar", "-f", help="Sin confirmación"),
) -> None:
    """Restaura ~/.keel/ desde un backup ZIP. Sobreescribe datos existentes."""
    import zipfile
    from keel.storage.local import keel_dir

    ruta_zip = Path(archivo)
    if not ruta_zip.exists():
        console.print(f"[red]Archivo no encontrado: {archivo}[/red]")
        raise typer.Exit(1)

    if not zipfile.is_zipfile(ruta_zip):
        console.print(f"[red]El archivo no es un ZIP válido: {archivo}[/red]")
        raise typer.Exit(1)

    directorio = keel_dir()

    with zipfile.ZipFile(ruta_zip, "r") as zf:
        nombres = zf.namelist()

    if not forzar:
        console.print(f"\n[yellow]Se restaurarán {len(nombres)} archivo(s) en {directorio}[/yellow]")
        console.print("[yellow]Los datos actuales serán sobreescritos.[/yellow]")
        if not Confirm.ask("¿Continuar?", default=False):
            console.print("[dim]Cancelado.[/dim]")
            raise typer.Exit(0)

    with zipfile.ZipFile(ruta_zip, "r") as zf:
        zf.extractall(directorio.parent)

    console.print(f"[green]✓ {len(nombres)} archivo(s) restaurado(s) en {directorio}[/green]")


@app.command()
def cifrar() -> None:
    """Activa el cifrado AES-256-GCM sobre ~/.keel/. Migración one-shot."""
    from keel.storage.local import keel_dir
    from keel.security.cifrado import cifrar as _cifrar, es_cifrado
    from keel.security.llave import obtener_clave
    from rich.prompt import Confirm

    directorio = keel_dir()
    marker = directorio / ".cifrado"

    if marker.exists():
        console.print("[yellow]El cifrado ya está activo.[/yellow]")
        raise typer.Exit(0)

    if not Confirm.ask(
        "\n[bold]¿Activar cifrado AES-256-GCM sobre ~/.keel/?[/bold]\n"
        "[dim]Los archivos JSON existentes se cifrarán en su lugar.\n"
        "La clave se guardará en el Keychain del sistema (o en ~/.keel/.key con permisos 0600).[/dim]\n",
        default=False,
    ):
        console.print("[dim]Cancelado.[/dim]")
        raise typer.Exit(0)

    clave = obtener_clave(directorio)

    # Cifra todos los JSON existentes
    archivos = list(directorio.glob("*.json")) + list((directorio / "personas").glob("*.json"))
    cifrados = 0
    for archivo in archivos:
        data = archivo.read_bytes()
        if not es_cifrado(data):
            archivo.write_bytes(_cifrar(data, clave))
            cifrados += 1

    marker.touch()
    console.print(f"[green]✓ Cifrado activado. {cifrados} archivo(s) protegido(s).[/green]")
    console.print("[dim]Usa `keel descifrar` para revertir si necesitas acceso directo a los JSON.[/dim]")


@app.command()
def descifrar() -> None:
    """Desactiva el cifrado y restaura los JSON a texto plano (export de emergencia)."""
    from keel.storage.local import keel_dir
    from keel.security.cifrado import descifrar as _descifrar, es_cifrado
    from keel.security.llave import obtener_clave
    from rich.prompt import Confirm

    directorio = keel_dir()
    marker = directorio / ".cifrado"

    if not marker.exists():
        console.print("[yellow]El cifrado no está activo.[/yellow]")
        raise typer.Exit(0)

    if not Confirm.ask(
        "\n[bold]¿Desactivar cifrado y restaurar JSON a texto plano?[/bold]",
        default=False,
    ):
        console.print("[dim]Cancelado.[/dim]")
        raise typer.Exit(0)

    clave = obtener_clave(directorio)

    archivos = list(directorio.glob("*.json")) + list((directorio / "personas").glob("*.json"))
    descifrados = 0
    for archivo in archivos:
        data = archivo.read_bytes()
        if es_cifrado(data):
            archivo.write_bytes(_descifrar(data, clave))
            descifrados += 1

    marker.unlink()
    console.print(f"[green]✓ Cifrado desactivado. {descifrados} archivo(s) restaurado(s).[/green]")


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


@app.command()
def ciclo(
    forzar: bool = typer.Option(False, "--forzar", "-f", help="Re-sintetiza aunque ya tenga síntesis del día"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Muestra qué haría sin modificar datos"),
    modelo: str = typer.Option(None, "--modelo", "-m"),
    ver_log: bool = typer.Option(False, "--ver-log", help="Muestra las últimas entradas del log y sale"),
) -> None:
    """Ciclo autónomo nocturno: sintetiza narrativas de todas las personas con historial.

    Diseñado para ejecutarse desde launchd cada noche. Registra el resultado
    en ~/.keel/logs/ciclo.log. Salida limpia incluso si Ollama no está disponible.

    Instala el ciclo nocturno con:
      bash ~/.local/share/keel-core/scripts/launchd/install-ciclo.sh
    """
    import datetime
    from keel.storage.local import cargar_perfil, keel_dir, cargar_config
    from keel.models.persona import Persona

    log_dir = keel_dir() / "logs"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / "ciclo.log"

    if ver_log:
        if not log_path.exists():
            console.print("[yellow]Sin log todavía. Ejecuta `keel ciclo` primero.[/yellow]")
            raise typer.Exit(0)
        lineas = log_path.read_text(encoding="utf-8").splitlines()
        for linea in lineas[-40:]:
            console.print(linea)
        raise typer.Exit(0)

    def _log(msg: str) -> None:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entrada = f"[{ts}] {msg}"
        console.print(f"[dim]{entrada}[/dim]")
        with log_path.open("a", encoding="utf-8") as f:
            f.write(entrada + "\n")

    cfg = cargar_config()
    if modelo is None and cfg.modelo_ollama:
        modelo = cfg.modelo_ollama

    hoy = datetime.date.today().isoformat()
    _log(f"── Ciclo iniciado {'(dry-run)' if dry_run else ''}")

    try:
        perfil = cargar_perfil()
    except FileNotFoundError:
        _log("ERROR: Perfil no encontrado. Ejecuta `keel init`.")
        raise typer.Exit(1)

    personas_dir = keel_dir() / "personas"
    archivos = sorted(personas_dir.glob("*.json")) if personas_dir.exists() else []
    todas = [Persona.model_validate_json(a.read_text()) for a in archivos]

    candidatas = [
        p for p in todas
        if p.historial_conversaciones and (forzar or p.ultima_sintesis != hoy)
    ]

    _log(f"{len(todas)} personas · {len(candidatas)} pendientes de síntesis")

    if not candidatas:
        _log("Sin personas nuevas que sintetizar. Usa --forzar para regenerar.")
        _log("── Ciclo completado")
        raise typer.Exit(0)

    if dry_run:
        for p in candidatas:
            console.print(f"  [dim]→ {p.nombre} ({len(p.historial_conversaciones)} conversaciones)[/dim]")
        _log(f"Dry-run: {len(candidatas)} personas se sintetizarían.")
        _log("── Ciclo completado (dry-run)")
        raise typer.Exit(0)

    from keel.llm.factory import crear_llm
    llm = crear_llm(cargar_config(), modelo_override=modelo or None)

    if not llm.disponible():
        _log("AVISO: Ollama no disponible — ciclo pospuesto hasta la próxima ejecución.")
        _log("── Ciclo completado (sin síntesis)")
        raise typer.Exit(0)  # Salida limpia: launchd no marca error

    # Leer contexto del calendario (falla silenciosamente si no disponible)
    contexto_agenda = ""
    try:
        from keel.io.calendario import leer_eventos_macos, resumir_agenda
        eventos = leer_eventos_macos(dias=7)
        if eventos:
            contexto_agenda = resumir_agenda(eventos, dias=7)
            _log(f"Calendario: {len(eventos)} evento(s) leído(s)")
        else:
            _log("Calendario: sin eventos o no disponible")
    except Exception as e:
        _log(f"Calendario: omitido ({e})")

    from keel.engine.sintesis import sintetizar_persona, aplicar_sintesis
    from keel.storage.local import guardar_persona

    ok = 0
    errores = 0
    for p in candidatas:
        try:
            sintesis = sintetizar_persona(p, perfil, llm, contexto_agenda=contexto_agenda)
            aplicar_sintesis(p, sintesis)
            guardar_persona(p)
            _log(f"✓ {p.nombre} [{sintesis.tipo_relacion}]: {sintesis.narrativa[:80]}…")
            ok += 1
        except Exception as e:
            _log(f"✗ {p.nombre}: {e}")
            errores += 1

    _log(f"── Ciclo completado: {ok} síntesis · {errores} errores")


@app.command()
def calendario(
    dias: int = typer.Option(7, "--dias", "-d", help="Días hacia adelante"),
    solo_contexto: bool = typer.Option(False, "--contexto", "-c", help="Muestra solo el contexto inferido"),
) -> None:
    """Muestra eventos próximos del Calendario de macOS e infiere el contexto situacional."""
    from keel.io.calendario import leer_eventos_macos, inferir_contexto_agenda, resumir_agenda
    from rich.table import Table
    from rich.rule import Rule

    import sys
    if sys.platform != "darwin":
        console.print("[yellow]El comando calendario requiere macOS.[/yellow]")
        raise typer.Exit(1)

    console.print(f"[dim]Leyendo eventos de los próximos {dias} días...[/dim]")
    eventos = leer_eventos_macos(dias=dias)

    if not eventos:
        console.print("[yellow]No se encontraron eventos o el Calendario no está disponible.[/yellow]")
        console.print("[dim]Asegúrate de que macOS Calendar tiene acceso a tus calendarios.[/dim]")
        raise typer.Exit(0)

    contexto = inferir_contexto_agenda(eventos, dias)

    if solo_contexto:
        if contexto:
            console.print(contexto)
        else:
            console.print("[dim]Sin patrón contextual detectado.[/dim]")
        raise typer.Exit(0)

    console.print()
    console.print(Rule(f"[bold]Agenda próximos {dias} días[/bold]"))
    console.print()

    tabla = Table(show_lines=False, box=None, padding=(0, 2))
    tabla.add_column("Fecha", style="dim", width=12)
    tabla.add_column("Hora", style="dim", width=6)
    tabla.add_column("Título")
    tabla.add_column("Calendario", style="dim", width=16)

    for e in sorted(eventos, key=lambda x: (x.fecha, x.hora)):
        tabla.add_row(e.fecha, e.hora, e.titulo, e.calendario)

    console.print(tabla)
    console.print(f"\n[dim]{len(eventos)} evento(s)[/dim]")

    if contexto:
        console.print(f"\n[bold]Contexto inferido:[/bold] {contexto}")


api_key_app = typer.Typer(help="Gestión de API keys de proveedores cloud.")
app.add_typer(api_key_app, name="api-key")


@api_key_app.command("set")
def api_key_set(
    proveedor: str = typer.Argument(..., help="anthropic | openai"),
    key: str = typer.Argument(..., help="API key del proveedor"),
) -> None:
    """Guarda la API key de un proveedor cloud en el Keychain (o archivo seguro)."""
    from keel.security.api_keys import guardar_api_key, proveedores_soportados
    if proveedor not in proveedores_soportados():
        console.print(f"[red]Proveedor '{proveedor}' no soportado. Opciones: {', '.join(proveedores_soportados())}[/red]")
        raise typer.Exit(1)
    guardar_api_key(proveedor, key)
    console.print(f"[green]✓ API key de {proveedor} guardada.[/green]")
    console.print(f"[dim]Para activar: keel config set proveedor {proveedor}[/dim]")


@api_key_app.command("get")
def api_key_get(
    proveedor: str = typer.Argument(..., help="anthropic | openai"),
) -> None:
    """Muestra si hay API key configurada para un proveedor (enmascarada)."""
    from keel.security.api_keys import obtener_api_key
    key = obtener_api_key(proveedor)
    if not key:
        console.print(f"[yellow]Sin API key configurada para '{proveedor}'.[/yellow]")
        console.print(f"[dim]Ejecuta: keel api-key set {proveedor} <tu-key>[/dim]")
        raise typer.Exit(1)
    mascara = key[:6] + "****" + key[-4:] if len(key) > 12 else "****"
    console.print(f"[green]✓[/green] {proveedor}: {mascara}")


@api_key_app.command("borrar")
def api_key_borrar(
    proveedor: str = typer.Argument(..., help="anthropic | openai"),
    forzar: bool = typer.Option(False, "--forzar", "-f", help="Sin confirmación"),
) -> None:
    """Elimina la API key de un proveedor del Keychain y archivos locales."""
    from keel.security.api_keys import eliminar_api_key
    if not forzar:
        confirmar = typer.confirm(f"¿Eliminar API key de '{proveedor}'?")
        if not confirmar:
            raise typer.Exit(0)
    eliminar_api_key(proveedor)
    console.print(f"[green]✓ API key de {proveedor} eliminada.[/green]")


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
