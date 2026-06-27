"""Subcomandos: keel notas add | ver | buscar | borrar."""

from datetime import date

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

app = typer.Typer(help="Gestiona notas personales.")
console = Console()


@app.command("add")
def add(
    contenido: str = typer.Argument(..., help="Contenido de la nota"),
    temas: str = typer.Option("", "--temas", "-t", help="Temas separados por coma (ej: proyecto,legal)"),
) -> None:
    """Agrega una nota personal al diario."""
    from keel.models.nota import Nota
    from keel.storage.local import agregar_nota

    lista_temas = [t.strip() for t in temas.split(",") if t.strip()] if temas else []
    nota = Nota(contenido=contenido, temas=lista_temas)
    agregar_nota(nota)

    temas_str = f" [{', '.join(lista_temas)}]" if lista_temas else ""
    console.print(f"[green]✓ Nota guardada [{nota.id}]{temas_str}: {contenido[:60]}[/green]")

    # Indexar en LanceDB si embedder disponible
    try:
        from keel.embedder.fastembed import FastEmbedder
        from keel.storage.vectorial import indexar_conversacion
        embedder = FastEmbedder()
        indexar_conversacion("_notas", nota.fecha, nota.contenido, lista_temas, embedder)
    except Exception:
        pass


@app.command("ver")
def ver(
    top: int = typer.Option(10, "--top", "-n", help="Número máximo de notas a mostrar"),
    desde: str = typer.Option(None, "--desde", help="Mostrar notas desde esta fecha (YYYY-MM-DD)"),
) -> None:
    """Muestra las notas más recientes."""
    from keel.storage.local import cargar_notas

    notas = cargar_notas()

    if desde:
        try:
            date.fromisoformat(desde)
        except ValueError:
            console.print(f"[red]Fecha inválida: '{desde}'. Usa YYYY-MM-DD.[/red]")
            raise typer.Exit(1)
        notas = [n for n in notas if n.fecha >= desde]

    notas = sorted(notas, key=lambda n: n.fecha, reverse=True)[:top]

    if not notas:
        console.print("[yellow]No hay notas registradas.[/yellow]")
        return

    tabla = Table(show_lines=True)
    tabla.add_column("ID", style="dim", width=10)
    tabla.add_column("Fecha", width=12)
    tabla.add_column("Contenido")
    tabla.add_column("Temas", width=20)

    for nota in notas:
        temas_str = ", ".join(nota.temas) if nota.temas else "—"
        tabla.add_row(nota.id, nota.fecha, nota.contenido, temas_str)

    console.print(tabla)
    console.print(f"\n[dim]{len(notas)} nota(s).[/dim]")


@app.command("buscar")
def buscar(
    texto: str = typer.Argument(..., help="Texto a buscar"),
    top: int = typer.Option(5, "--top", "-n"),
    sin_vectores: bool = typer.Option(False, "--sin-vectores"),
) -> None:
    """Busca en las notas por contenido o tema."""
    from keel.storage.local import cargar_notas
    from keel.engine.busqueda import buscar_notas as _buscar

    notas = cargar_notas()

    embedder = None
    if not sin_vectores:
        try:
            from keel.embedder.fastembed import FastEmbedder
            embedder = FastEmbedder()
        except Exception:
            pass

    resultados = _buscar(texto, notas, embedder=embedder, top=top)

    if not resultados:
        console.print(f"[yellow]Sin resultados para '{texto}'.[/yellow]")
        return

    tabla = Table(show_lines=True)
    tabla.add_column("Fecha", width=12)
    tabla.add_column("Nota")
    tabla.add_column("Temas", width=20)
    tabla.add_column("Modo", width=10, style="dim")

    for r in resultados:
        temas = r.get("temas", "")
        if isinstance(temas, list):
            temas = ", ".join(temas)
        tabla.add_row(r["fecha"], r["resumen"], temas or "—", r.get("modo", ""))

    console.print(tabla)
    console.print(f"\n[dim]{len(resultados)} resultado(s).[/dim]")


@app.command("editar")
def editar(
    nota_id: str = typer.Argument(..., help="ID de la nota a editar"),
    contenido: str = typer.Option(None, "--contenido", "-c", help="Nuevo contenido"),
    temas: str = typer.Option(None, "--temas", "-t", help="Nuevos temas (reemplaza los actuales, separados por coma)"),
) -> None:
    """Edita el contenido o los temas de una nota existente."""
    import os, tempfile, subprocess
    from keel.storage.local import cargar_notas, guardar_notas

    notas = cargar_notas()
    nota = next((n for n in notas if n.id == nota_id), None)

    if not nota:
        console.print(f"[red]Nota '{nota_id}' no encontrada.[/red]")
        raise typer.Exit(1)

    if contenido is None and temas is None:
        # Abrir en $EDITOR
        editor = os.environ.get("EDITOR", "nano")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
            tmp.write(nota.contenido)
            tmp_path = tmp.name
        try:
            subprocess.run([editor, tmp_path], check=True)
            nuevo = open(tmp_path).read().strip()
        finally:
            os.unlink(tmp_path)
        if not nuevo:
            console.print("[yellow]Contenido vacío — no se guardó.[/yellow]")
            raise typer.Exit(0)
        nota.contenido = nuevo
    else:
        if contenido is not None:
            nota.contenido = contenido
        if temas is not None:
            nota.temas = [t.strip() for t in temas.split(",") if t.strip()]

    guardar_notas(notas)
    temas_str = f" [{', '.join(nota.temas)}]" if nota.temas else ""
    console.print(f"[green]✓ Nota {nota_id} actualizada{temas_str}: {nota.contenido[:60]}[/green]")


@app.command("borrar")
def borrar(
    nota_id: str = typer.Argument(..., help="ID de la nota a borrar"),
    forzar: bool = typer.Option(False, "--forzar", "-f"),
) -> None:
    """Elimina una nota por su ID."""
    from keel.storage.local import cargar_notas, eliminar_nota

    notas = cargar_notas()
    nota = next((n for n in notas if n.id == nota_id), None)

    if not nota:
        console.print(f"[red]Nota '{nota_id}' no encontrada.[/red]")
        raise typer.Exit(1)

    console.print(f"Nota: [cyan]{nota.contenido[:80]}[/cyan]")

    if not forzar and not Confirm.ask("¿Eliminar esta nota?", default=False):
        console.print("[dim]Cancelado.[/dim]")
        raise typer.Exit(0)

    eliminar_nota(nota_id)
    console.print(f"[green]✓ Nota {nota_id} eliminada.[/green]")
