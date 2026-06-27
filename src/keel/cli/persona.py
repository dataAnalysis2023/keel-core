"""Subcomandos: keel persona add | list | show | renombrar | eliminar | editar | fusionar."""

import json
import subprocess
import os
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm

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
    tabla.add_column("Última interacción", style="dim")

    for archivo in archivos:
        p = Persona.model_validate_json(archivo.read_text())
        tabla.add_row(
            p.nombre,
            p.rol or "—",
            p.tono_relacional,
            str(len(p.historial_conversaciones)),
            str(len(p.promesas_pendientes)),
            p.ultima_interaccion or "—",
        )

    console.print(tabla)


@app.command("show")
def show(
    nombre: str = typer.Argument(...),
    recientes: int = typer.Option(5, "--recientes", "-n", help="Conversaciones recientes a mostrar"),
    raw: bool = typer.Option(False, "--raw", help="Vuelca el JSON sin formato"),
) -> None:
    """Muestra el perfil enriquecido de una persona: datos, temas, promesas e historial."""
    from datetime import date
    from collections import Counter
    from rich.rule import Rule

    persona = cargar_persona(nombre)

    if raw:
        console.print(
            Panel(persona.model_dump_json(indent=2), title=f"[bold]{persona.nombre}[/bold]", border_style="blue")
        )
        return

    console.print()
    console.print(Rule(f"[bold]{persona.nombre}[/bold]"))
    console.print()

    # ── Datos de perfil ───────────────────────────────────────────────────────
    filas_perfil = []
    if persona.rol:
        filas_perfil.append(("Rol", persona.rol))
    if persona.como_nos_conocemos:
        filas_perfil.append(("Contexto", persona.como_nos_conocemos))
    if persona.tono_relacional and persona.tono_relacional != "neutro":
        filas_perfil.append(("Tono", persona.tono_relacional))
    if persona.estado_actual:
        filas_perfil.append(("Estado actual", persona.estado_actual))
    if persona.sensibilidades:
        filas_perfil.append(("Sensibilidades", ", ".join(persona.sensibilidades)))

    if persona.ultima_interaccion:
        try:
            dias = (date.today() - date.fromisoformat(persona.ultima_interaccion)).days
            filas_perfil.append(("Última interacción", f"{persona.ultima_interaccion} (hace {dias}d)"))
        except ValueError:
            filas_perfil.append(("Última interacción", persona.ultima_interaccion))

    if filas_perfil:
        tabla_perfil = Table(show_header=False, box=None, padding=(0, 2))
        tabla_perfil.add_column("Campo", style="dim", width=20)
        tabla_perfil.add_column("Valor")
        for k, v in filas_perfil:
            tabla_perfil.add_row(k, v)
        console.print(tabla_perfil)
        console.print()

    # ── Temas frecuentes ──────────────────────────────────────────────────────
    contador: Counter = Counter()
    for conv in persona.historial_conversaciones:
        for tema in conv.temas:
            if tema.strip():
                contador[tema.strip().lower()] += 1
    temas_top = [t for t, n in contador.most_common(8) if n > 1]
    if temas_top:
        temas_str = "  ".join(f"[cyan]{t}[/cyan] [dim]×{contador[t]}[/dim]" for t in temas_top)
        console.print(f"[bold]Temas frecuentes:[/bold]  {temas_str}")
        console.print()

    # ── Promesas pendientes ───────────────────────────────────────────────────
    if persona.promesas_pendientes:
        hoy = date.today().isoformat()
        tabla_prom = Table(title="Compromisos pendientes", show_lines=False, box=None, padding=(0, 2))
        tabla_prom.add_column("", width=2)
        tabla_prom.add_column("Descripción")
        tabla_prom.add_column("Fecha", style="dim", width=14)
        for pr in persona.promesas_pendientes:
            fecha = pr.fecha_compromiso or ""
            if fecha and fecha < hoy:
                icon = "🔴"
                fecha_str = f"[red]{fecha}[/red]"
            elif fecha and fecha <= (date.today().replace(day=date.today().day)).isoformat():
                icon = "🟡"
                fecha_str = fecha
            else:
                icon = "🟢" if fecha else "·"
                fecha_str = fecha or "—"
            tabla_prom.add_row(icon, pr.descripcion, fecha_str)
        console.print(tabla_prom)
        console.print()

    # ── Historial reciente ────────────────────────────────────────────────────
    entradas = sorted(persona.historial_conversaciones, key=lambda c: c.fecha)[-recientes:]
    total = len(persona.historial_conversaciones)
    if entradas:
        titulo = f"Últimas {len(entradas)} conversaciones" + (f" (de {total})" if total > recientes else "")
        tabla_hist = Table(title=titulo, show_lines=False, box=None, padding=(0, 2))
        tabla_hist.add_column("Fecha", style="dim", width=12)
        tabla_hist.add_column("Resumen")
        tabla_hist.add_column("Temas", style="dim", width=20)
        for c in entradas:
            tabla_hist.add_row(c.fecha, c.resumen, ", ".join(c.temas) if c.temas else "—")
        console.print(tabla_hist)
    elif not filas_perfil and not persona.promesas_pendientes:
        console.print(f"[dim]Persona sin datos aún. Usa `keel persona add {nombre}` para agregar detalles.[/dim]")

    console.print()


@app.command("renombrar")
def renombrar(
    viejo: str = typer.Argument(..., help="Nombre actual"),
    nuevo: str = typer.Argument(..., help="Nombre nuevo"),
) -> None:
    """Renombra una persona: actualiza el archivo y el campo nombre."""
    personas_dir = keel_dir() / "personas"
    origen = personas_dir / f"{viejo.lower()}.json"

    if not origen.exists():
        console.print(f"[red]No existe persona '{viejo}'.[/red]")
        raise typer.Exit(1)

    destino = personas_dir / f"{nuevo.lower()}.json"
    if destino.exists():
        console.print(f"[red]Ya existe una persona llamada '{nuevo}'. Usa `fusionar` si quieres combinarlas.[/red]")
        raise typer.Exit(1)

    persona = Persona.model_validate_json(origen.read_text())
    persona.nombre = nuevo
    guardar_persona(persona)
    origen.unlink()

    console.print(f"[green]✓ '{viejo}' renombrada a '{nuevo}'.[/green]")


@app.command("eliminar")
def eliminar(
    nombre: str = typer.Argument(..., help="Nombre de la persona a eliminar"),
    forzar: bool = typer.Option(False, "--forzar", "-f", help="Sin confirmación"),
) -> None:
    """Elimina una persona y su historial del grafo de relaciones."""
    personas_dir = keel_dir() / "personas"
    ruta = personas_dir / f"{nombre.lower()}.json"

    if not ruta.exists():
        console.print(f"[red]No existe persona '{nombre}'.[/red]")
        raise typer.Exit(1)

    persona = Persona.model_validate_json(ruta.read_text())
    conversaciones = len(persona.historial_conversaciones)
    promesas = len(persona.promesas_pendientes)

    if not forzar:
        console.print(
            f"\n[yellow]Esto eliminará a {nombre} con {conversaciones} conversación(es) "
            f"y {promesas} promesa(s) pendiente(s).[/yellow]"
        )
        if not Confirm.ask("¿Confirmar eliminación?", default=False):
            console.print("[dim]Cancelado.[/dim]")
            raise typer.Exit(0)

    ruta.unlink()
    console.print(f"[green]✓ '{nombre}' eliminada del grafo de relaciones.[/green]")
    console.print("[dim]Nota: los vectores en LanceDB no se eliminan automáticamente.[/dim]")


@app.command("editar")
def editar(nombre: str = typer.Argument(..., help="Nombre de la persona")) -> None:
    """Abre el perfil de la persona en $EDITOR para edición directa."""
    personas_dir = keel_dir() / "personas"
    ruta = personas_dir / f"{nombre.lower()}.json"

    if not ruta.exists():
        console.print(f"[yellow]'{nombre}' no existe aún. Creando perfil vacío...[/yellow]")
        persona = Persona(nombre=nombre)
        guardar_persona(persona)

    editor = os.environ.get("EDITOR", "nano")
    subprocess.run([editor, str(ruta)])

    # Valida JSON después de edición
    try:
        Persona.model_validate_json(ruta.read_text())
        console.print(f"[green]✓ Perfil de {nombre} guardado correctamente.[/green]")
    except Exception as e:
        console.print(f"[red]El JSON editado no es válido: {e}[/red]")
        console.print("[yellow]El archivo se guardó igual — revísalo con `keel persona show`.[/yellow]")


@app.command("fusionar")
def fusionar(
    origen: str = typer.Argument(..., help="Persona cuyos datos se absorben"),
    destino: str = typer.Argument(..., help="Persona que recibe los datos"),
    forzar: bool = typer.Option(False, "--forzar", "-f"),
) -> None:
    """Fusiona dos personas: mueve el historial de ORIGEN a DESTINO y elimina ORIGEN."""
    personas_dir = keel_dir() / "personas"
    ruta_origen = personas_dir / f"{origen.lower()}.json"
    ruta_destino = personas_dir / f"{destino.lower()}.json"

    if not ruta_origen.exists():
        console.print(f"[red]No existe persona origen '{origen}'.[/red]")
        raise typer.Exit(1)
    if not ruta_destino.exists():
        console.print(f"[red]No existe persona destino '{destino}'.[/red]")
        raise typer.Exit(1)

    p_origen = Persona.model_validate_json(ruta_origen.read_text())
    p_destino = Persona.model_validate_json(ruta_destino.read_text())

    conv_a_mover = len(p_origen.historial_conversaciones)
    prom_a_mover = len(p_origen.promesas_pendientes)

    if not forzar:
        console.print(
            f"\nSe moverán {conv_a_mover} conversación(es) y {prom_a_mover} "
            f"promesa(s) de [bold]{origen}[/bold] → [bold]{destino}[/bold]."
        )
        if not Confirm.ask("¿Confirmar fusión?", default=False):
            console.print("[dim]Cancelado.[/dim]")
            raise typer.Exit(0)

    # Combinar historial (deduplicar por fecha+resumen)
    existentes = {(c.fecha, c.resumen) for c in p_destino.historial_conversaciones}
    for conv in p_origen.historial_conversaciones:
        if (conv.fecha, conv.resumen) not in existentes:
            p_destino.historial_conversaciones.append(conv)
            existentes.add((conv.fecha, conv.resumen))

    # Combinar promesas
    existentes_prom = {p.descripcion for p in p_destino.promesas_pendientes}
    for prom in p_origen.promesas_pendientes:
        if prom.descripcion not in existentes_prom:
            p_destino.promesas_pendientes.append(prom)

    # Combinar sensibilidades
    p_destino.sensibilidades = list(set(p_destino.sensibilidades + p_origen.sensibilidades))

    # Ordenar historial cronológicamente
    p_destino.historial_conversaciones.sort(key=lambda c: c.fecha)

    guardar_persona(p_destino)
    ruta_origen.unlink()

    console.print(
        f"[green]✓ Fusión completa: {conv_a_mover} conversación(es) y "
        f"{prom_a_mover} promesa(s) movidas a '{destino}'. '{origen}' eliminada.[/green]"
    )
