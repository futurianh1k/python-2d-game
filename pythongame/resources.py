"""Locate bundled assets independently of the current working directory."""

from pathlib import Path

# PyInstaller preserves this layout inside its bundle as well.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = PROJECT_ROOT / "resources" / "fonts"


def resource_path(path: str | Path) -> Path:
    """Resolve a project-relative asset path, preserving absolute paths."""
    return PROJECT_ROOT / path
