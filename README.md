# 🖼️ Picture Puller CLI (iQIYI Carousel Asset Extractor)

A cross-platform command-line application designed for university academic research and multimedia coursework. It navigates to streaming platforms (specifically **iQIYI**), injects an in-browser extraction script into the client runtime context, and downloads the top carousel series separated into **3 distinct visual layers**:

1. 🌄 **Background Artwork** (`bg/bg.<ext>`)
2. 👤 **Character Cutout / Focus** (`character/character.<ext>`)
3. 🏷️ **Series Logo / Title Artwork** (`logo/logo.<ext>`)

Each series also includes a rich `metadata.json` containing the synopsis, genre tags, audience rating, score, and original CDN URLs.

---

## 🖥️ Multi-OS Compatibility

Picture Puller is fully compatible with:
* 🐧 **Linux**: **Fedora / RHEL**, **Ubuntu / Debian**, **Arch Linux**, openSUSE
* 🍏 **macOS**: Intel & Apple Silicon (M1/M2/M3/M4)
* 🪟 **Windows**: Windows 10 & 11 (PowerShell / Command Prompt)

The application includes an **intelligent browser launcher** that automatically detects your OS and resolves the best available browser engine:
1. Custom `--browser-path` or `--channel` (if specified)
2. Bundled Playwright Chromium
3. System-installed Chromium (`/usr/bin/chromium`, etc.)
4. System-installed Google Chrome or Microsoft Edge

---

## 📁 Output Folder Structure

When executed, the CLI creates a numbered directory hierarchy maintaining the original carousel display ranking:

```text
output/
├── 01_LOVEx3/
│   ├── bg/
│   │   └── bg.webp               # High-res background banner
│   ├── character/
│   │   └── character.webp        # Transparent character cutout / focus
│   ├── logo/
│   │   └── logo.png              # Transparent series logo artwork
│   └── metadata.json             # Title, synopsis, tags, rating & CDN links
├── 02_Your_Third/
│   ├── bg/
│   ├── character/
│   ├── logo/
│   └── metadata.json
├── 03_Mr.Fanboy/
│   └── ...
├── 04_Genius_Girlfriend_(Thai_ver.)/
│   └── ...
├── 05_OVERDO_(Thai_ver.)/
│   └── ...
└── 06_KNOT/
    └── ...
```

---

## 🛠️ Installation & Setup by Operating System

### 1. Common Setup (All Operating Systems)

First, clone or navigate into the project directory and create a virtual environment:

```bash
# Clone or open directory
cd /path/to/PicturePullerVibe

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment:
# On Linux / macOS:
source .venv/bin/activate
# On Windows (PowerShell):
# .\.venv\bin\Activate.ps1
# On Windows (cmd):
# .\.venv\bin\activate.bat

# Install Python requirements
pip install -r requirements.txt
```

---

### 2. Browser Engine Setup per OS

#### 🔵 Fedora Linux / RHEL / CentOS
> [!NOTE]
> When running `playwright install chromium` on Fedora, you may see:
> ```text
> BEWARE: your OS is not officially supported by Playwright; downloading fallback build for ubuntu24.04-x64.
> ```
> **This warning is harmless**: Playwright uses the fallback build which runs smoothly on modern Fedora releases.

You have two simple options on Fedora:

* **Option A (Recommended — Bundled Fallback)**:
  ```bash
  playwright install chromium
  ```
* **Option B (Native Fedora DNF Chromium)**:
  If you prefer using Fedora's native package manager:
  ```bash
  sudo dnf install -y chromium
  ```
  Then run the CLI specifying the channel:
  ```bash
  python main.py pull --channel chromium
  ```
  *(Or if system libraries are missing for Option A, install them via `sudo dnf install -y nss libXcomposite libXdamage libXrandr mesa-libgbm alsa-lib pango cairo`)*

---

#### 🟠 Ubuntu / Debian Linux
```bash
# Install Playwright browser and system dependencies:
playwright install chromium
playwright install-deps

# Or use system Chromium:
sudo apt install -y chromium-browser
python main.py pull --channel chromium
```

---

#### 🟣 Arch Linux / Manjaro
```bash
# Option A: Playwright bundled build
playwright install chromium

# Option B: Native Arch package
sudo pacman -S chromium
python main.py pull --channel chromium
```

---

#### 🍏 macOS (Intel & Apple Silicon)
```bash
# Option A: Playwright bundled build
playwright install chromium

# Option B: Existing Google Chrome or Edge
python main.py pull --channel chrome
# or:
python main.py pull --channel msedge
```

---

#### 🪟 Windows (10 / 11)
```powershell
# Option A: Playwright bundled build
playwright install chromium

# Option B: Use built-in Microsoft Edge (no extra downloads needed!)
python main.py pull --channel msedge

# Option C: Use installed Google Chrome
python main.py pull --channel chrome
```

---

## 📖 How to Use

### 1. Default Run (Pulls 6 Recommended Series)
Run the script directly with default parameters (`https://www.iq.com/?lang=en_th` saving into `./output`):
```bash
python main.py pull
```

### 2. Preview First (Dry Run Mode)
Extracts and displays all series titles and image layers in a formatted terminal table without saving any files:
```bash
python main.py pull --dry-run
```

### 3. Specify Custom Output Directory
Save downloaded images to a custom directory:
```bash
python main.py pull -o ./university_assets
```

### 4. Custom Series Count
Extract more or fewer carousel slides (e.g., top 3 series):
```bash
python main.py pull -n 3
```

### 5. Visual Debugging (Headed Mode)
Open a visible browser window to observe page loading and script execution:
```bash
python main.py pull --headed
```

### 6. Using a System Browser / Channel
```bash
# Linux (Fedora / Ubuntu / Arch)
python main.py pull --channel chromium

# macOS / Windows
python main.py pull --channel chrome
python main.py pull --channel msedge

# Or provide exact binary path
python main.py pull --browser-path /usr/bin/chromium
```

### 7. Custom Injection Script
Inject your own JavaScript extractor snippet into the browser:
```bash
python main.py pull --script scripts/iqiyi_extractor.js
```

---

## ⚙️ CLI Command Reference

```text
Usage: main.py pull [OPTIONS]

Options:
  -u, --url TEXT          Target webpage URL containing the recommend carousel
                          [default: https://www.iq.com/?lang=en_th]
  -o, --output PATH       Directory to save downloaded series and images
                          [default: output]
  -n, --count INTEGER     Number of series to extract and download (default: 6)
                          [default: 6]
  -s, --script PATH       Path to custom JavaScript extraction script to inject
      --headed            Run browser in visible/headed mode (useful for debugging)
      --dry-run           Preview extracted series and image URLs without downloading
      --timeout INTEGER   Page load timeout in milliseconds [default: 35000]
  -c, --channel TEXT      Browser channel to use ('chromium', 'chrome', 'msedge')
  -b, --browser-path PATH Custom path to installed browser executable
  --help                  Show this message and exit.
```

---

## 🧩 Technical Architecture & Script Injection

1. **Resilient Browser Engine (`src/picture_puller/browser.py`)**:
   Launches Playwright Chromium or falls back to system-installed Chrome/Chromium/Edge across Linux, macOS, and Windows.
2. **In-Browser Script Injection (`scripts/iqiyi_extractor.js`)**:
   Injected into the live page execution context. Queries React component Fiber state (`focusImgInfo`) and Next.js internal data to pull high-res layered assets.
3. **Async Downloader (`src/picture_puller/downloader.py`)**:
   Streams image assets concurrently using `httpx` with proper HTTP headers (`Referer`, `User-Agent`). Organizes assets into isolated `bg/`, `character/`, and `logo/` folders and exports `metadata.json`.

---

## 🎓 Academic Compliance & Fair Use Notice

This tool was created solely for an **educational, non-profit university project**. 
* All image assets and trademarks belong to their respective copyright holders (iQIYI and production studios).
* Assets must not be distributed, republished, or used for commercial gain.
* Respect website terms of service and avoid excessive automated requests.
