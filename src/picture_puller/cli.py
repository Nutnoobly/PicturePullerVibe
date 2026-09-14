"""
Command-line interface handlers for Picture Puller Vibe.
Provides Typer commands and Rich terminal interfaces for image pulling.
"""

import asyncio
from pathlib import Path
from typing import Optional, List
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from . import __version__
from .models import SeriesItem, DownloadResult
from .browser import extract_series_with_browser
from .downloader import download_all_series

app = typer.Typer(
    name="picture-puller",
    help="CLI to pull layered carousel series pictures via script injection.",
    add_completion=False
)
console = Console()


def _render_series_table(target_series: List[SeriesItem]) -> None:
    """
    Renders a formatted table of extracted series items and detected layers.
    """
    table = Table(title=f"Extracted {len(target_series)} Series from Carousel", show_lines=True)
    table.add_column("#", justify="center", style="dim", width=4)
    table.add_column("Title", style="bold cyan", min_width=20)
    table.add_column("Background (bg)", justify="center")
    table.add_column("Character Focus", justify="center")
    table.add_column("Series Logo", justify="center")
    table.add_column("Tags", style="dim")

    for s in target_series:
        bg_status = "[green]✓ Found[/green]" if s.bg_url else "[red]✗ Missing[/red]"
        char_status = "[green]✓ Found[/green]" if s.character_url else "[yellow]— None[/yellow]"
        logo_status = "[green]✓ Found[/green]" if s.logo_url else "[yellow]— None[/yellow]"
        tags_str = ", ".join(s.tags[:3]) if s.tags else "-"
        table.add_row(str(s.index), s.title, bg_status, char_status, logo_status, tags_str)

    console.print(table)


def _render_summary_table(results: List[DownloadResult], output_dir: Path) -> None:
    """
    Renders a summary table of downloaded assets and file locations.
    """
    summary_table = Table(title="Download Results Summary", show_lines=True)
    summary_table.add_column("Series Folder", style="bold white")
    summary_table.add_column("Background", justify="center")
    summary_table.add_column("Character", justify="center")
    summary_table.add_column("Logo", justify="center")
    summary_table.add_column("Metadata JSON", justify="center")

    total_images = 0
    for r in results:
        bg_sym = "[green]✓ Saved[/green]" if r.bg_path else "[red]✗ Missing[/red]"
        char_sym = "[green]✓ Saved[/green]" if r.character_path else "[yellow]— None[/yellow]"
        logo_sym = "[green]✓ Saved[/green]" if r.logo_path else "[yellow]— None[/yellow]"
        meta_sym = "[green]✓ Saved[/green]" if r.metadata_path else "[red]✗ Failed[/red]"

        if r.bg_path:
            total_images += 1
        if r.character_path:
            total_images += 1
        if r.logo_path:
            total_images += 1

        folder_name = Path(r.folder_path).name
        summary_table.add_row(folder_name, bg_sym, char_sym, logo_sym, meta_sym)

    console.print(summary_table)
    console.print(
        f"\n[bold green]✨ Successfully downloaded {total_images} assets "
        f"across {len(results)} series into:[/bold green] [cyan]{output_dir.resolve()}[/cyan]"
    )


@app.command(name="pull")
def pull(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    url: str = typer.Option(
        "https://www.iq.com/?lang=en_th",
        "--url", "-u",
        help="Target webpage URL containing the recommend carousel"
    ),
    output: Path = typer.Option(
        Path("./output"),
        "--output", "-o",
        help="Directory to save downloaded series and images"
    ),
    count: int = typer.Option(
        6,
        "--count", "-n",
        help="Number of series to extract and download (default: 6)"
    ),
    script: Optional[Path] = typer.Option(
        None,
        "--script", "-s",
        help="Path to custom JavaScript extraction script to inject into the page"
    ),
    headed: bool = typer.Option(
        False,
        "--headed",
        help="Run browser in visible/headed mode (useful for debugging)"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview extracted series and image URLs without downloading"
    ),
    timeout: int = typer.Option(
        35000,
        "--timeout",
        help="Page load timeout in milliseconds (default: 35000)"
    ),
    channel: Optional[str] = typer.Option(
        None,
        "--channel", "-c",
        help="Browser channel to use (e.g., 'chromium', 'chrome', 'msedge')"
    ),
    browser_path: Optional[Path] = typer.Option(
        None,
        "--browser-path", "-b",
        help="Custom path to an installed browser executable (Chrome/Chromium/Edge)"
    )
):
    """
    Extract and download layered series images (background, character cutout, logo) from target.
    """
    mode_text = (
        "[magenta]Dry Run (Preview Only)[/magenta]"
        if dry_run
        else "[green]Live Download[/green]"
    )
    panel_content = (
        f"[bold cyan]Picture Puller CLI[/bold cyan]\n"
        f"[dim]Target URL:[/dim] [white]{url}[/white]\n"
        f"[dim]Output Folder:[/dim] [green]{output}[/green]\n"
        f"[dim]Requested Series Count:[/dim] [yellow]{count}[/yellow]\n"
        f"[dim]Execution Mode:[/dim] {mode_text}"
    )
    if channel:
        panel_content += f"\n[dim]Browser Channel:[/dim] [magenta]{channel}[/magenta]"
    if browser_path:
        panel_content += f"\n[dim]Browser Path:[/dim] [magenta]{browser_path}[/magenta]"

    console.print(Panel.fit(panel_content, border_style="cyan"))

    with console.status("[bold green]Launching browser and injecting script...[/bold green]"):
        try:
            series_list = asyncio.run(
                extract_series_with_browser(
                    url=url,
                    custom_script_path=str(script) if script else None,
                    headed=headed,
                    channel=channel,
                    browser_path=str(browser_path) if browser_path else None,
                    timeout_ms=timeout
                )
            )
        except Exception as err:
            console.print(f"[bold red]Extraction failed:[/bold red] {err}")
            raise typer.Exit(code=1) from err

    if not series_list:
        console.print("[bold red]No series items were found or extracted from the page.[/bold red]")
        raise typer.Exit(code=1)

    target_series = series_list[:count]
    _render_series_table(target_series)

    if dry_run:
        console.print("\n[magenta]Dry-run enabled: Skipped file downloads.[/magenta]")
        return

    console.print(
        f"\n[bold green]Starting download for {len(target_series)} series...[/bold green]"
    )
    results = asyncio.run(download_all_series(target_series, output))
    _render_summary_table(results, output)


@app.command(name="version")
def version():
    """Display CLI version."""
    console.print(f"[cyan]picture-puller[/cyan] version [bold green]{__version__}[/bold green]")


def main():
    """CLI application entry point."""
    app()


if __name__ == "__main__":
    main()
