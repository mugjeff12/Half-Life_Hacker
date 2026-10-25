"""Where things live — works from source and from a PyInstaller bundle."""
import sys
from pathlib import Path


def base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def asset(*parts: str) -> Path:
    return base_dir().joinpath("assets", *parts)
