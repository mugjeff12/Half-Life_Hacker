"""Render LaTeX-ish equations to crisp PNGs (matplotlib mathtext) for the lesson text."""
import base64
import io
from functools import lru_cache

from PIL import Image
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from .theme import INK

_DPI = 220
_SCALE = 96.0 / _DPI * 1.0   # px in the PNG -> logical px in the text view


@lru_cache(maxsize=None)
def _render(tex: str, size: float, color: str):
    fig = Figure(dpi=_DPI)
    FigureCanvasAgg(fig)
    fig.text(0.5, 0.5, f"${tex}$", fontsize=size, color=color, ha="center", va="center")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=_DPI, transparent=True, bbox_inches="tight", pad_inches=0.05)
    data = buf.getvalue()
    w, h = Image.open(io.BytesIO(data)).size
    return base64.b64encode(data).decode("ascii"), w, h


def img(tex: str, size: float = 15, color: str = INK) -> str:
    b64, w, h = _render(tex, size, color)
    return f'<img src="data:image/png;base64,{b64}" width="{round(w * _SCALE)}" height="{round(h * _SCALE)}"/>'


def eq(tex: str, size: float = 16) -> str:
    """A centred display equation."""
    return f'<p align="center" style="margin-top:6px;margin-bottom:6px">{img(tex, size)}</p>'
