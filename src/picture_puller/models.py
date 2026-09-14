"""
Pydantic data models representing extracted series items and download results.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class SeriesItem(BaseModel):
    """
    Represents a single carousel series with its metadata and layered image URLs.
    """
    index: int = Field(default=1, description="1-based index in the carousel order")
    title: str = Field(..., description="Series title")
    bg_url: Optional[str] = Field(None, description="Background image URL")
    character_url: Optional[str] = Field(None, description="Character focus / cutout image URL")
    logo_url: Optional[str] = Field(None, description="Series title / logo image URL")
    desc: Optional[str] = Field(default="", description="Synopsis or description")
    score: Optional[str] = Field(default=None, description="Audience/critic score")
    year: Optional[str] = Field(default=None, description="Release year")
    rating: Optional[str] = Field(default=None, description="Age rating")
    tags: List[str] = Field(default_factory=list, description="Category/genre tags")
    play_link: Optional[str] = Field(default=None, description="Direct watch link")


class DownloadResult(BaseModel):
    """
    Represents the output filesystem paths and layer status for a downloaded series.
    """
    series_title: str
    folder_path: str
    bg_path: Optional[str] = None
    character_path: Optional[str] = None
    logo_path: Optional[str] = None
    metadata_path: Optional[str] = None
    missing_layers: List[str] = Field(default_factory=list)
