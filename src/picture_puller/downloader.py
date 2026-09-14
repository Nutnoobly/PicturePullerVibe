import json
import asyncio
from pathlib import Path
from typing import List, Optional
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
    except Exception as e:
        console.print(f"[red]Error downloading {url}: {e}[/red]")
        return False


async def download_series_assets(
    client: httpx.AsyncClient,
    series: SeriesItem,
    output_dir: Path
) -> DownloadResult:
    """
    Downloads all 3 layers (bg, character, logo) for a single series and saves metadata.json.
    Creates folder structure:
      <output_dir>/<01_title>/
        ├── bg/bg.<ext>
        ├── character/character.<ext>
        ├── logo/logo.<ext>
        └── metadata.json
    """
    folder_name = format_series_folder_name(series.index, series.title)
    series_dir = output_dir / folder_name
    series_dir.mkdir(parents=True, exist_ok=True)

    bg_dir = series_dir / "bg"
    char_dir = series_dir / "character"
    logo_dir = series_dir / "logo"

    bg_dir.mkdir(parents=True, exist_ok=True)
    char_dir.mkdir(parents=True, exist_ok=True)
    logo_dir.mkdir(parents=True, exist_ok=True)

    result = DownloadResult(
        series_title=series.title,
        folder_path=str(series_dir)
    )

    tasks = []

    # 1. Background image
    if series.bg_url:
        bg_ext = get_extension_from_url(series.bg_url, default=".webp")
        bg_dest = bg_dir / f"bg{bg_ext}"
        tasks.append(("bg", series.bg_url, bg_dest))
    else:
        result.missing_layers.append("bg")
        console.print(f"[yellow]⚠️  [{series.title}] Missing background layer (bg_url)[/yellow]")

    # 2. Character focus image
    if series.character_url:
        char_ext = get_extension_from_url(series.character_url, default=".webp")
        char_dest = char_dir / f"character{char_ext}"
        tasks.append(("character", series.character_url, char_dest))
    else:
        result.missing_layers.append("character")
        console.print(f"[yellow]⚠️  [{series.title}] Missing character focus layer (character_url)[/yellow]")

    # 3. Logo image
    if series.logo_url:
        logo_ext = get_extension_from_url(series.logo_url, default=".png")
        logo_dest = logo_dir / f"logo{logo_ext}"
        tasks.append(("logo", series.logo_url, logo_dest))
    else:
        result.missing_layers.append("logo")
        console.print(f"[yellow]⚠️  [{series.title}] Missing series logo layer (logo_url)[/yellow]")

    # Execute downloads concurrently for this series
    for layer_type, url, dest in tasks:
        success = await download_file(client, url, dest)
        if success:
            if layer_type == "bg":
                result.bg_path = str(dest)
            elif layer_type == "character":
                result.character_path = str(dest)
            elif layer_type == "logo":
                result.logo_path = str(dest)
        else:
            result.missing_layers.append(layer_type)

    # 4. Save metadata.json
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
        "saved_files": {
            "bg": result.bg_path,
            "character": result.character_path,
            "logo": result.logo_path
        },
        "missing_layers": result.missing_layers
    }

    meta_file = series_dir / "metadata.json"
    meta_file.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    result.metadata_path = str(meta_file)

    return result


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
            task = progress.add_task("[green]Downloading series assets...", total=len(series_list))
            
            for item in series_list:
                progress.update(task, description=f"[green]Downloading:[/green] [bold]{item.title}[/bold]")
                res = await download_series_assets(client, item, output_dir)
                results.append(res)
                progress.advance(task)

    return results
