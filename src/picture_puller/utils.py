"""
Utility functions for filename sanitization, extension inference, and folder naming.
"""

import re
from urllib.parse import urlparse


def sanitize_filename(name: str, max_length: int = 80) -> str:
    """
    Sanitizes a string to be safely used as a folder or file name across OSes.
    Replaces problematic characters with underscores and trims length.
    """
    if not name:
        return "unnamed"
    # Replace illegal filesystem chars
    clean = re.sub(r'[\\/*?:"<>|]', '_', name)
    # Collapse multiple spaces or underscores
    clean = re.sub(r'[\s_]+', '_', clean)
    clean = clean.strip(' ._')
    if len(clean) > max_length:
        clean = clean[:max_length].rstrip(' ._')
    return clean or "unnamed"


def get_extension_from_url(url: str, default: str = ".jpg") -> str:
    """
    Infers the image extension from a URL path, stripping query parameters.
    """
    if not url:
        return default
    parsed = urlparse(url)
    path = parsed.path.lower()
    for ext in [".png", ".webp", ".jpg", ".jpeg", ".gif", ".svg", ".avif"]:
        if path.endswith(ext):
            return ext
    # Default based on typical formats
    return default


def format_series_folder_name(index: int, title: str) -> str:
    """
    Formats the numbered series folder name, e.g.: '01_LOVEx3'
    """
    clean_title = sanitize_filename(title)
    return f"{index:02d}_{clean_title}"
