"""Subcomandos: keel agenda ver | add | completar | posponer | borrar | notificar."""

import subprocess
import sys
from datetime import date, timedelta

import typer
from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table

from keel.storage.local import cargar_persona, guardar_persona, keel_dir
from keel.models.persona import Persona

app = typer.Typer(help="Gestiona compromisos y promesas pendientes.")
console = Console()


@app.command("add")
def add(
    persona: str = typer.Option(..., "--persona", "-p", help="Nombre de la persona"),
    descripcion: str = typer.Option(..., "--descripcion", "-d", help="Descripción del compromiso"),
    fecha: str = typer.Option(None, "--fecha", "-f", help="Fecha límite YYYY-MM-DD (opcional)"),
) -> None:
    """Agrega una promesa pendiente directamente a la agenda."""
    if fecha:
        try:
            date.fromisoformat(fecha)
        except ValueError:
            console.print(f"[red]Fecha inválida: '{fecha}'. Usa formato YYYY-MM-DD.[/red]")
            raise typer.Exit(1)

    from keel.models.persona import PromesaPendiente
    p = cargar_persona(persona)
    p.promesas_pendientes.append(PromesaPendiente(descripcion=descripcion, fecha_compromiso=fecha))
    guardar_persona(p)

    fecha_str = f" (hasta {fecha})" if fecha else ""
    console.print(f"[green]✓ Promesa agregada a {persona}: '{descripcion}'{fecha_str}[/green]")


@app.command("ver")
def ver(
    persona: str = typer.Option(None, "--persona", "-p", help="Filtrar por persona"),
) -> None:
    """Muestra las promesas pendientes. Filtra con --persona."""
    personas_dir = keel_dir() / "personas"
    archivos = sorted(personas_dir.glob("*.json")) if personas_dir.exists() else []

    pendientes: list[tuple[str, int, object]] = []
    for archivo in archivos:
        p = Persona.model_validate_json(archivo.read_text())
        if persona and p.nombre.lower() != persona.lower():
            continue
        for idx, promesa in enumerate(p.promesas_pendientes):
            pendientes.append((p.nombre, idx, promesa))

    if not pendientes:
        console.print("[green]Sin promesas pendientes.[/green]")
        return

    hoy = date.today().isoformat()
    tabla = Table(title="Agenda de compromisos", show_lines=True)
    tabla.add_column("#", style="dim", width=4)
    tabla.add_column("Con quién", style="bold")
    tabla.add_column("Compromiso")
    tabla.add_column("Fecha límite")
    tabla.add_column("Estado", width=10)

    for nombre, idx, promesa in pendientes:
        fecha = promesa.fecha_compromiso or ""
        if fecha and fecha < hoy:
            estado = "[red]VENCIDA[/red]"
            fecha_str = f"[red]{fecha}[/red]"
        elif fecha and fecha == hoy:
            estado = "[yellow]HOY[/yellow]"
            fecha_str = f"[yellow]{fecha}[/yellow]"
        elif fecha and fecha <= (date.today() + timedelta(days=2)).isoformat():
            estado = "[yellow]PRÓXIMA[/yellow]"
            fecha_str = fecha
        else:
            estado = ""
            fecha_str = fecha or "—"

        tabla.add_row(str(idx), nombre, promesa.descripcion, fecha_str, estado)

    console.print(tabla)
    console.print(f"\n[dim]{len(pendientes)} compromiso(s) en total.[/dim]")


@app.command("completar")
def completar(
    persona: str = typer.Option(..., "--persona", "-p", help="Nombre de la persona"),
    indice: int = typer.Option(None, "--indice", "-i", help="Índice de la promesa (ver con `keel agenda ver`)"),
    descripcion: str = typer.Option("", "--descripcion", "-d", help="Texto parcial para identificar la promesa"),
    forzar: bool = typer.Option(False, "--forzar", "-f"),
) -> None:
    """Marca una promesa como cumplida y la elimina de la agenda."""
    p = cargar_persona(persona)

    if not p.promesas_pendientes:
        console.print(f"[yellow]{persona} no tiene promesas pendientes.[/yellow]")
        raise typer.Exit(0)

    # Resolver cuál promesa
    if indice is not None:
        if indice < 0 or indice >= len(p.promesas_pendientes):
            console.print(f"[red]Índice {indice} fuera de rango (0-{len(p.promesas_pendientes)-1}).[/red]")
            raise typer.Exit(1)
        idx = indice
    elif descripcion:
        coincidencias = [
            i for i, pr in enumerate(p.promesas_pendientes)
            if descripcion.lower() in pr.descripcion.lower()
        ]
        if len(coincidencias) == 0:
            console.print(f"[red]Ninguna promesa contiene '{descripcion}'.[/red]")
            raise typer.Exit(1)
        if len(coincidencias) > 1:
            console.print(f"[yellow]Varias coincidencias: usa --indice. Usa `keel agenda ver` para ver los índices.[/yellow]")
            raise typer.Exit(1)
        idx = coincidencias[0]
    else:
        console.print("[red]Usa --indice o --descripcion para identificar la promesa.[/red]")
        raise typer.Exit(1)

    promesa = p.promesas_pendientes[idx]

    if not forzar and not Confirm.ask(
        f"¿Marcar como cumplida: '[cyan]{promesa.descripcion}[/cyan]'?",
        default=True,
    ):
        console.print("[dim]Cancelado.[/dim]")
        raise typer.Exit(0)

    p.promesas_pendientes.pop(idx)
    guardar_persona(p)
    console.print(f"[green]✓ Promesa completada y retirada de la agenda de {persona}.[/green]")


@app.command("posponer")
def posponer(
    persona: str = typer.Option(..., "--persona", "-p"),
    indice: int = typer.Option(..., "--indice", "-i", help="Índice de la promesa"),
    fecha: str = typer.Option(..., "--fecha", help="Nueva fecha límite (YYYY-MM-DD)"),
) -> None:
    """Cambia la fecha límite de una promesa pendiente."""
    # Validar fecha
    try:
        date.fromisoformat(fecha)
    except ValueError:
        console.print(f"[red]Fecha inválida: '{fecha}'. Usa formato YYYY-MM-DD.[/red]")
        raise typer.Exit(1)

    p = cargar_persona(persona)

    if indice < 0 or indice >= len(p.promesas_pendientes):
        console.print(f"[red]Índice {indice} fuera de rango.[/red]")
        raise typer.Exit(1)

    promesa = p.promesas_pendientes[indice]
    fecha_anterior = promesa.fecha_compromiso or "sin fecha"
    promesa.fecha_compromiso = fecha
    guardar_persona(p)

    console.print(
        f"[green]✓ '{promesa.descripcion}' pospuesta de {fecha_anterior} → {fecha}.[/green]"
    )


@app.command("borrar")
def borrar(
    persona: str = typer.Option(..., "--persona", "-p", help="Nombre de la persona"),
    indice: int = typer.Option(None, "--indice", "-i", help="Índice de la promesa"),
    descripcion: str = typer.Option("", "--descripcion", "-d", help="Texto parcial para identificar la promesa"),
    forzar: bool = typer.Option(False, "--forzar", "-f"),
) -> None:
    """Elimina una promesa pendiente (sin marcarla como cumplida)."""
    p = cargar_persona(persona)

    if not p.promesas_pendientes:
        console.print(f"[yellow]{persona} no tiene promesas pendientes.[/yellow]")
        raise typer.Exit(0)

    if indice is not None:
        if indice < 0 or indice >= len(p.promesas_pendientes):
            console.print(f"[red]Índice {indice} fuera de rango (0-{len(p.promesas_pendientes)-1}).[/red]")
            raise typer.Exit(1)
        idx = indice
    elif descripcion:
        coincidencias = [
            i for i, pr in enumerate(p.promesas_pendientes)
            if descripcion.lower() in pr.descripcion.lower()
        ]
        if len(coincidencias) == 0:
            console.print(f"[red]Ninguna promesa contiene '{descripcion}'.[/red]")
            raise typer.Exit(1)
        if len(coincidencias) > 1:
            console.print("[yellow]Varias coincidencias: usa --indice.[/yellow]")
            raise typer.Exit(1)
        idx = coincidencias[0]
    else:
        console.print("[red]Usa --indice o --descripcion para identificar la promesa.[/red]")
        raise typer.Exit(1)

    promesa = p.promesas_pendientes[idx]

    if not forzar and not Confirm.ask(
        f"¿Eliminar promesa: '[cyan]{promesa.descripcion}[/cyan]'?",
        default=False,
    ):
        console.print("[dim]Cancelado.[/dim]")
        raise typer.Exit(0)

    p.promesas_pendientes.pop(idx)
    guardar_persona(p)
    console.print(f"[green]✓ Promesa eliminada de la agenda de {persona}.[/green]")


@app.command("notificar")
def notificar(
    dias: int = typer.Option(2, "--dias", "-d", help="Alertar si vence en <= N días"),
) -> None:
    """Envía notificaciones macOS por promesas próximas a vencer.

    Útil para ejecutar desde launchd cada mañana:
      keel agenda notificar
    """
    if sys.platform != "darwin":
        console.print("[yellow]Las notificaciones solo están disponibles en macOS.[/yellow]")
        raise typer.Exit(1)

    personas_dir = keel_dir() / "personas"
    archivos = sorted(personas_dir.glob("*.json")) if personas_dir.exists() else []

    hoy = date.today()
    limite = (hoy + timedelta(days=dias)).isoformat()
    hoy_str = hoy.isoformat()

    urgentes = []
    for archivo in archivos:
        p = Persona.model_validate_json(archivo.read_text())
        for promesa in p.promesas_pendientes:
            if promesa.fecha_compromiso and promesa.fecha_compromiso <= limite:
                urgentes.append((p.nombre, promesa))

    if not urgentes:
        console.print("[green]Sin compromisos urgentes en los próximos días.[/green]")
        return

    for nombre, promesa in urgentes:
        vencida = promesa.fecha_compromiso < hoy_str
        if vencida:
            titulo = f"⚠ Keel — Promesa vencida con {nombre}"
        elif promesa.fecha_compromiso == hoy_str:
            titulo = f"🔴 Keel — Promesa HOY con {nombre}"
        else:
            titulo = f"🟡 Keel — Promesa próxima con {nombre}"

        mensaje = promesa.descripcion[:100]
        _notificacion_macos(titulo, mensaje)
        console.print(f"[dim]Notificación: {titulo}[/dim]")

    console.print(f"\n[green]✓ {len(urgentes)} notificación(es) enviada(s).[/green]")
    console.print(
        "[dim]Para ejecutarlo automáticamente cada mañana:\n"
        "  bash ~/.local/share/keel-core/scripts/launchd/install-notificaciones.sh[/dim]"
    )


def _notificacion_macos(titulo: str, mensaje: str) -> None:
    script = (
        f'display notification "{mensaje}" '
        f'with title "{titulo}" '
        f'sound name "default"'
    )
    subprocess.run(["osascript", "-e", script], capture_output=True)
