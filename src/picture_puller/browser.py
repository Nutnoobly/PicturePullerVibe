"""
Playwright browser automation and in-browser script injection module.
Provides resilient multi-OS browser launching and series data extraction.
"""

import os
import shutil
import platform
import asyncio
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from playwright.async_api import async_playwright, Browser, Playwright, Error as PlaywrightError
from rich.console import Console

from .models import SeriesItem

console = Console()

DEFAULT_SCRIPT_PATH = (
    Path(__file__).resolve().parent.parent.parent / "scripts" / "iqiyi_extractor.js"
)

DEFAULT_CHROMIUM_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-blink-features=AutomationControlled",
    "--disable-gpu",
]


def detect_system_os() -> str:
    """
    Detects the current operating system and Linux distribution family.
    Returns: 'fedora', 'rhel', 'ubuntu', 'debian', 'arch', 'linux',
    'macos', 'windows', or 'unknown'.
    """
    system = platform.system()
    if system == "Linux":
        if os.path.exists("/etc/os-release"):
            try:
                with open("/etc/os-release", encoding="utf-8") as file:
                    content = file.read().lower()
                distro_map = {
                    "fedora": "fedora",
                    "rhel": "rhel",
                    "centos": "rhel",
                    "rocky": "rhel",
                    "almalinux": "rhel",
                    "ubuntu": "ubuntu",
                    "debian": "debian",
                    "arch": "arch",
                    "manjaro": "arch",
                }
                for key, mapped in distro_map.items():
                    if key in content:
                        return mapped
            except OSError:
                pass
        return "linux"

    os_map = {"Darwin": "macos", "Windows": "windows"}
    return os_map.get(system, "unknown")


def get_os_browser_advice(os_name: str) -> str:
    """
    Generates OS-specific installation advice if Playwright browser launch fails.
    """
    advice_map = {
        "fedora": (
            "[bold yellow]Fedora / RHEL Fix:[/bold yellow]\n"
            "Playwright uses Ubuntu-compiled binaries by default. On Fedora, you can:\n"
            "  1. Install native Chromium via DNF and run with the channel flag:\n"
            "     [bold cyan]sudo dnf install -y chromium[/bold cyan]\n"
            "     [bold green]python main.py pull --channel chromium[/bold green]\n"
            "  2. Or install required system libraries:\n"
            "     [bold cyan]sudo dnf install -y nss libXcomposite libXdamage "
            "libXrandr mesa-libgbm alsa-lib pango cairo[/bold cyan]"
        ),
        "rhel": (
            "[bold yellow]RHEL Fix:[/bold yellow]\n"
            "Install Chromium via EPEL or run: [bold cyan]sudo dnf install -y chromium[/bold cyan]"
        ),
        "ubuntu": (
            "[bold yellow]Ubuntu / Debian Fix:[/bold yellow]\n"
            "Install required browser dependencies:\n"
            "  [bold cyan]playwright install-deps[/bold cyan]\n"
            "  OR install Chromium: [bold cyan]sudo apt install -y chromium-browser[/bold cyan]\n"
            "  Then run: [bold green]python main.py pull --channel chromium[/bold green]"
        ),
        "debian": (
            "[bold yellow]Debian Fix:[/bold yellow]\n"
            "Install dependencies: [bold cyan]playwright install-deps[/bold cyan]"
        ),
        "arch": (
            "[bold yellow]Arch Linux Fix:[/bold yellow]\n"
            "Install native Chromium:\n"
            "  [bold cyan]sudo pacman -S chromium[/bold cyan]\n"
            "  Then run: [bold green]python main.py pull --channel chromium[/bold green]"
        ),
        "macos": (
            "[bold yellow]macOS Fix:[/bold yellow]\n"
            "Run: [bold cyan]playwright install chromium[/bold cyan]\n"
            "Or use Chrome: [bold green]python main.py pull --channel chrome[/bold green]"
        ),
        "windows": (
            "[bold yellow]Windows Fix:[/bold yellow]\n"
            "Run: [bold cyan]playwright install chromium[/bold cyan]\n"
            "Or use Edge: [bold green]python main.py pull --channel msedge[/bold green]"
        ),
    }

    return advice_map.get(
        os_name,
        (
            "[bold yellow]Troubleshooting:[/bold yellow]\n"
            "Run: [bold cyan]playwright install chromium[/bold cyan]\n"
            "Or pass an installed browser: [bold green]--browser-path <path>[/bold green]"
        )
    )


def find_system_browser_path() -> Optional[str]:
    """
    Scans common executable names and paths across Fedora, Ubuntu, macOS, and Windows.
    """
    candidates: List[str] = []
    if platform.system() == "Windows":
        prog_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        prog_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        local_app = os.environ.get("LocalAppData", "")
        candidates.extend([
            os.path.join(prog_files, r"Google\Chrome\Application\chrome.exe"),
            os.path.join(prog_files_x86, r"Google\Chrome\Application\chrome.exe"),
            os.path.join(prog_files, r"Microsoft\Edge\Application\msedge.exe"),
            os.path.join(prog_files_x86, r"Microsoft\Edge\Application\msedge.exe"),
            os.path.join(local_app, r"Google\Chrome\Application\chrome.exe"),
        ])
    elif platform.system() == "Darwin":
        candidates.extend([
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        ])
    else:
        for bin_name in ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]:
            found = shutil.which(bin_name)
            if found:
                candidates.append(found)

    for path_str in candidates:
        if path_str and os.path.exists(path_str) and os.access(path_str, os.X_OK):
            return path_str
    return None


async def launch_resilient_browser(
    playwright: Playwright,
    headed: bool = False,
    channel: Optional[str] = None,
    executable_path: Optional[str] = None
) -> Tuple[Browser, str]:
    """
    Attempts to launch the browser using a multi-step fallback hierarchy:
    1. Custom executable_path
    2. Custom channel
    3. Playwright bundled Chromium
    4. Auto-detected system browser channels ('chromium', 'chrome', 'msedge')
    5. Auto-detected system binary path
    """
    launch_attempts: List[Tuple[str, Dict[str, Any]]] = []

    if executable_path:
        launch_attempts.append(("Custom Path", {"executable_path": executable_path}))

    if channel:
        launch_attempts.append((f"Channel '{channel}'", {"channel": channel}))

    launch_attempts.append(("Playwright Bundled Chromium", {}))

    for ch in ["chromium", "chrome", "msedge"]:
        if not channel or channel != ch:
            launch_attempts.append((f"Fallback Channel '{ch}'", {"channel": ch}))

    sys_path = find_system_browser_path()
    if sys_path and (not executable_path or executable_path != sys_path):
        launch_attempts.append((f"System Binary ({sys_path})", {"executable_path": sys_path}))

    last_error: Optional[Exception] = None
    for description, kwargs in launch_attempts:
        try:
            browser = await playwright.chromium.launch(
                headless=not headed,
                args=DEFAULT_CHROMIUM_ARGS,
                **kwargs
            )
            return browser, description
        except (PlaywrightError, OSError, RuntimeError) as err:
            last_error = err
            continue

    os_name = detect_system_os()
    advice = get_os_browser_advice(os_name)
    console.print(f"\n[bold red]Failed to launch any browser.[/bold red] Last error: {last_error}")
    console.print(f"\n{advice}\n")
    raise RuntimeError(f"Could not launch browser on {os_name.capitalize()}: {last_error}")


async def extract_series_with_browser(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    url: str,
    custom_script_path: Optional[str] = None,
    headed: bool = False,
    channel: Optional[str] = None,
    browser_path: Optional[str] = None,
    timeout_ms: int = 35000,
    settle_delay_sec: float = 4.0
) -> List[SeriesItem]:
    """
    Launches browser, navigates to target URL, injects extractor script,
    and returns a list of validated SeriesItem objects.
    """
    script_file = Path(custom_script_path) if custom_script_path else DEFAULT_SCRIPT_PATH
    if not script_file.exists():
        raise FileNotFoundError(f"Extractor script file not found at: {script_file}")

    script_content = script_file.read_text(encoding="utf-8")

    async with async_playwright() as playwright:
        browser, used_launch = await launch_resilient_browser(
            playwright,
            headed=headed,
            channel=channel,
            executable_path=browser_path
        )
        console.print(f"[dim]Browser engine launched using:[/dim] [green]{used_launch}[/green]")

        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            locale="en-US"
        )
        page = await context.new_page()

        try:
            console.print(f"[dim]Navigating to:[/dim] [cyan]{url}[/cyan]")
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

            await asyncio.sleep(settle_delay_sec)

            console.print(
                f"[dim]Injecting extractor script:[/dim] [magenta]{script_file.name}[/magenta]"
            )
            raw_data = await page.evaluate(script_content)

            if not raw_data or not isinstance(raw_data, list):
                raw_data = await page.evaluate(f"() => {{ return {script_content.strip()}; }}")
                if not raw_data or not isinstance(raw_data, list):
                    console.print("[yellow]Warning: Injected script returned empty data.[/yellow]")
                    return []

            series_list = []
            for item in raw_data:
                try:
                    series_list.append(SeriesItem(**item))
                except (ValueError, TypeError, KeyError) as err:
                    console.print(f"[yellow]Skipping invalid series data: {err}[/yellow]")

            return series_list

        finally:
            await context.close()
            await browser.close()
