"""
Asynchronous image downloader and directory organizer.
Streams layered assets concurrently and saves structured metadata.
"""

# pylint: disable=import-error
import json
from pathlib import Path
from typing import List, Tuple
import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn

from .models import SeriesItem, DownloadResult
from .utils import format_series_folder_name, get_extension_from_url

console = Console()

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.iq.com/",
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
}


async def download_file(
    client: httpx.AsyncClient,
    url: str,
    destination: Path
) -> bool:
    """
    Downloads a single image from a URL to destination.
    """
    try:
        response = await client.get(url, timeout=20.0)
        response.raise_for_status()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(response.content)
        return True
    except (httpx.HTTPError, OSError) as e:
        console.print(f"[red]Error downloading {url}: {e}[/red]")
        return False


def _build_layer_tasks(
    series: SeriesItem,
    series_dir: Path
) -> Tuple[List[Tuple[str, str, Path]], List[str]]:
    """
    Constructs the download tasks and detects any missing layers for a series.
    """
    tasks: List[Tuple[str, str, Path]] = []
    missing_layers: List[str] = []

    # 1. Background image
    if series.bg_url:
        bg_ext = get_extension_from_url(series.bg_url, default=".webp")
        bg_dest = series_dir / "bg" / f"bg{bg_ext}"
        tasks.append(("bg", series.bg_url, bg_dest))
    else:
        missing_layers.append("bg")
        console.print(f"[yellow]⚠️  [{series.title}] Missing background layer[/yellow]")

    # 2. Character focus image
    if series.character_url:
        char_ext = get_extension_from_url(series.character_url, default=".webp")
        char_dest = series_dir / "character" / f"character{char_ext}"
        tasks.append(("character", series.character_url, char_dest))
    else:
        missing_layers.append("character")
        console.print(f"[yellow]⚠️  [{series.title}] Missing character focus layer[/yellow]")

    # 3. Logo image
    if series.logo_url:
        logo_ext = get_extension_from_url(series.logo_url, default=".png")
        logo_dest = series_dir / "logo" / f"logo{logo_ext}"
        tasks.append(("logo", series.logo_url, logo_dest))
    else:
        missing_layers.append("logo")
        console.print(f"[yellow]⚠️  [{series.title}] Missing series logo layer[/yellow]")

    return tasks, missing_layers


def _save_metadata(
    series: SeriesItem,
    series_dir: Path,
    saved_files: dict,
    missing_layers: List[str]
) -> str:
    """
    Saves structured series metadata and original CDN URLs to metadata.json.
    """
    metadata = {
        "index": series.index,
        "title": series.title,
        "description": series.desc,
        "tags": series.tags,
        "score": series.score,
        "year": series.year,
        "rating": series.rating,
        "play_link": series.play_link,
        "source_urls": {
            "bg": series.bg_url,
            "character": series.character_url,
            "logo": series.logo_url
        },
        "saved_files": saved_files,
        "missing_layers": missing_layers
    }
    meta_file = series_dir / "metadata.json"
    meta_file.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(meta_file)


async def download_series_assets(
    client: httpx.AsyncClient,
    series: SeriesItem,
    output_dir: Path
) -> DownloadResult:
    """
    Downloads all 3 layers (bg, character, logo) for a single series and saves metadata.json.
    """
    folder_name = format_series_folder_name(series.index, series.title)
    series_dir = output_dir / folder_name
    series_dir.mkdir(parents=True, exist_ok=True)

    tasks, missing_layers = _build_layer_tasks(series, series_dir)
    failed_layers = list(missing_layers)
    saved_paths = {"bg": None, "character": None, "logo": None}

    for layer_type, url, dest in tasks:
        success = await download_file(client, url, dest)
        if success:
            saved_paths[layer_type] = str(dest)
        else:
            failed_layers.append(layer_type)

    meta_path = _save_metadata(series, series_dir, saved_paths, failed_layers)

    return DownloadResult(
        series_title=series.title,
        folder_path=str(series_dir),
        bg_path=saved_paths["bg"],
        character_path=saved_paths["character"],
        logo_path=saved_paths["logo"],
        metadata_path=meta_path,
        missing_layers=failed_layers
    )


async def download_all_series(
    series_list: List[SeriesItem],
    output_dir: Path
) -> List[DownloadResult]:
    """
    Downloads assets for all series in the list with progress reporting.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []

    async with httpx.AsyncClient(headers=DEFAULT_HEADERS, follow_redirects=True) as client:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            task = progress.add_task("[green]Downloading series...", total=len(series_list))

            for item in series_list:
                status_desc = f"[green]Downloading:[/green] [bold]{item.title}[/bold]"
                progress.update(task, description=status_desc)
                res = await download_series_assets(client, item, output_dir)
                results.append(res)
                progress.advance(task)

    return results
