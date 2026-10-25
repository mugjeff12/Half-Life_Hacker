"""Reusable widgets: banner, rich lesson view, console, plot panel."""
from __future__ import annotations

import pickle
import textwrap

from PySide6.QtCore import QRectF, Qt, QUrl, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPixmap, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (QFileDialog, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QScrollArea,
                               QSizePolicy, QStackedLayout, QTextBrowser, QVBoxLayout, QWidget)

from . import theme
from .editor import mono_font
from .paths import asset

_PIX_CACHE: dict = {}


def pixmap(path) -> QPixmap:
    key = str(path)
    if key not in _PIX_CACHE:
        _PIX_CACHE[key] = QPixmap(key)
    return _PIX_CACHE[key]


# ----------------------------------------------------------------------------- banner
class BannerLabel(QWidget):
    """Photo banner (cover-cropped) with a brand overlay, or a brand gradient when there is no photo."""

    def __init__(self, image_key: str, focus: float, kicker: str, title: str, parent=None):
        super().__init__(parent)
        self.key, self.focus, self.kicker, self.title = image_key, focus, kicker, title
        self.setFixedHeight(132)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        r = self.rect()
        path_clip = QRectF(r)
        p.setClipRect(path_clip)
        if self.key:
            pm = pixmap(asset("img", f"{self.key}.jpg"))
            if not pm.isNull():
                tw, th = r.width(), r.height()
                scale = max(tw / pm.width(), th / pm.height())
                sw, sh = tw / scale, th / scale
                sy = max(0.0, min(pm.height() - sh, (pm.height() - sh) * self.focus))
                p.drawPixmap(QRectF(0, 0, tw, th), pm, QRectF((pm.width() - sw) / 2, sy, sw, sh))
        else:
            g = QLinearGradient(0, 0, r.width(), 0)
            g.setColorAt(0, QColor(theme.MAROON))
            g.setColorAt(1, QColor(theme.BLACK))
            p.fillRect(r, g)
            logo = pixmap(asset("naygn_logo.png"))
            p.setOpacity(0.35)
            p.drawPixmap(QRectF(r.width() - 170, -20, 190, 190), logo, QRectF(logo.rect()))
            p.setOpacity(1)
        g = QLinearGradient(0, 0, r.width() * 0.75, 0)
        g.setColorAt(0, QColor(11, 11, 11, 235))
        g.setColorAt(1, QColor(11, 11, 11, 20))
        p.fillRect(r, g)
        p.fillRect(QRectF(0, r.height() - 4, r.width(), 4), QColor(theme.MAROON))
        f = QFont(self.font())
        f.setPointSizeF(9.5)
        f.setBold(True)
        f.setLetterSpacing(QFont.AbsoluteSpacing, 2.2)
        p.setFont(f)
        p.setPen(QColor("#FF8FB3"))
        p.drawText(QRectF(24, 26, r.width() - 48, 22), Qt.AlignLeft | Qt.AlignVCenter, self.kicker.upper())
        f2 = QFont(self.font())
        f2.setPointSizeF(21)
        f2.setBold(True)
        p.setFont(f2)
        p.setPen(QColor("#FFFFFF"))
        p.drawText(QRectF(24, 50, r.width() - 48, 56), Qt.AlignLeft | Qt.AlignVCenter, self.title)


# ----------------------------------------------------------------------------- lesson text
LESSON_CSS = f"""
h1 {{ color: {theme.MAROON}; font-size: 20pt; font-weight: 700; margin-top: 2px; margin-bottom: 6px; }}
h3 {{ color: {theme.INK}; font-size: 12.5pt; margin-top: 12px; margin-bottom: 3px; }}
p, li {{ font-size: 11pt; line-height: 135%; }}
li {{ margin-bottom: 4px; }}
code {{ font-family: 'Cascadia Mono','Consolas','Menlo','DejaVu Sans Mono'; color: {theme.MAROON}; background-color: #F3EAEE; }}
a {{ color: {theme.MAROON}; }}
td {{ font-size: 10.5pt; }}
"""


class RichView(QTextBrowser):
    def __init__(self, html: str, parent=None):
        super().__init__(parent)
        self.setOpenExternalLinks(True)
        self.document().setDefaultStyleSheet(LESSON_CSS)
        self.setHtml(html)
        self._zoom = 0

    def set_zoom(self, steps: int):
        d = steps - self._zoom
        if d > 0:
            self.zoomIn(d)
        elif d < 0:
            self.zoomOut(-d)
        self._zoom = steps


# ----------------------------------------------------------------------------- console
class OutputConsole(QPlainTextEdit):
    COLORS = {"out": "#E8E8E8", "ok": theme.OK_GREEN, "bad": theme.BAD_ROSE, "warn": theme.WARN_AMBER,
              "hint": "#FFB3CC", "err": theme.BAD_ROSE, "info": "#9A9A9A"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(mono_font(10.5))
        self.setLineWrapMode(QPlainTextEdit.WidgetWidth)

    def add(self, text: str, kind: str = "out"):
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(self.COLORS[kind]))
        if kind == "hint":
            fmt.setFontItalic(True)
        cur = self.textCursor()
        cur.movePosition(QTextCursor.End)
        if self.document().characterCount() > 1:
            cur.insertBlock()
        cur.insertText(text, fmt)
        self.setTextCursor(cur)
        self.ensureCursorVisible()

    def add_output(self, output: str):
        for line in output.splitlines():
            s = line.lstrip()
            kind = ("ok" if s.startswith("✓") else "bad" if s.startswith("✗") else
                    "warn" if s.startswith("⏳") else "hint" if s.startswith("hint:") else "out")
            self.add(line, kind)

    def set_point_size(self, pt):
        f = self.font()
        f.setPointSizeF(pt)
        self.setFont(f)


# ----------------------------------------------------------------------------- plots
def fit_titles(fig):
    """Wrap / shrink axes titles so they never run off a (possibly narrow) panel."""
    try:
        r = fig.canvas.get_renderer()
    except Exception:
        return
    W = fig.get_figwidth() * fig.dpi
    for ax in fig.axes:
        base = getattr(ax, "_hlh_title", None)
        if base is None:
            base = ax._hlh_title = (ax.get_title(), ax.title.get_fontsize())
        txt, fs = base
        if not txt:
            continue
        avail = 0.97 * W * ax.get_position().width
        wrapped = textwrap.fill(txt, width=max(14, len(txt) // 2 + 6))
        for cand, size in ((txt, fs), (wrapped, fs), (wrapped, max(9, fs - 2)), (wrapped, 9)):
            ax.set_title(cand, fontsize=size)
            widest = max(ax.title.get_window_extent(r).width, 0)
            if widest <= avail:
                break


class PlotWindow(QWidget):
    """Big, separate window for the plots (zoom / pan / save toolbar). Gets a fresh copy of the figures on every run."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent, Qt.Window)
        self.setWindowTitle(f"Plot — {title}")
        ico = asset("naygn.ico")
        if ico.exists():
            self.setWindowIcon(QIcon(str(ico)))
        self.resize(1180, 760)
        self.setMinimumSize(560, 380)
        self._col = QVBoxLayout(self)
        self._col.setContentsMargins(8, 8, 8, 8)
        self._col.setSpacing(4)
        self._widgets = []
        self.msg = QLabel()
        self.msg.setAlignment(Qt.AlignCenter)
        self.msg.setStyleSheet(f"color:{theme.MUTED}; font-size: 12pt;")
        self._col.addWidget(self.msg)

    def _clear(self):
        for w in self._widgets:
            self._col.removeWidget(w)
            w.setParent(None)
            w.deleteLater()
        self._widgets = []

    def set_figures(self, figs):
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
        self._clear()
        if not figs:
            self.msg.show()
            self.msg.setText("Nothing to show yet — press ▶ Run in the main window.")
            return
        self.msg.hide()
        for fig in figs:
            fig.set_dpi(100)
            fig.set_layout_engine("constrained")
            canvas = FigureCanvasQTAgg(fig)
            canvas.setMinimumHeight(420)
            canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            canvas.mpl_connect("resize_event", lambda ev, f=fig: fit_titles(f))
            bar = NavigationToolbar2QT(canvas, self)
            for w in (bar, canvas):
                self._col.addWidget(w, 1 if w is canvas else 0)
                self._widgets.append(w)


class PlotPanel(QWidget):
    """Holds the matplotlib canvases for the latest run (or a friendly message)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._figs = []
        self._stack = QStackedLayout(self)
        self.msg = QLabel()
        self.msg.setWordWrap(True)
        self.msg.setAlignment(Qt.AlignCenter)
        self.msg.setStyleSheet(f"color:{theme.MUTED}; font-size: 11pt; padding: 24px;")
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.inner = QWidget()
        self.col = QVBoxLayout(self.inner)
        self.col.setContentsMargins(6, 6, 6, 6)
        self.scroll.setWidget(self.inner)
        self._stack.addWidget(self.msg)
        self._stack.addWidget(self.scroll)
        self._pop = None
        self._title = ""
        self.show_message("Press ▶ Run — your plot appears here.")

    def set_title(self, title: str):
        self._title = title

    def pop_out(self):
        """Open (or raise) the big plot window."""
        if self._pop is None:
            self._pop = PlotWindow(self._title, self.window())
        self._refresh_pop()
        self._pop.show()
        self._pop.raise_()
        self._pop.activateWindow()

    def _refresh_pop(self):
        if self._pop is None:
            return
        copies = []
        for fig in self._figs:
            try:
                copies.append(pickle.loads(pickle.dumps(fig)))   # independent copy: the panel keeps its own
            except Exception:
                pass
        self._pop.set_figures(copies)

    def close_pop(self):
        if self._pop is not None:
            self._pop.close()
            self._pop.deleteLater()
            self._pop = None

    def clear(self):
        while self.col.count():
            item = self.col.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._figs = []

    def show_message(self, text: str):
        self.clear()
        self.msg.setText(text)
        self._stack.setCurrentWidget(self.msg)
        if self._pop is not None and self._pop.isVisible():
            self._pop.set_figures([])

    def set_figures(self, figs):
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        self.clear()
        if not figs:
            return
        for fig in figs:
            fig.set_dpi(78)   # app panels are smaller than a notebook page: keep text proportionate
            fig.set_layout_engine("constrained")
            canvas = FigureCanvasQTAgg(fig)
            canvas.setMinimumSize(420, 230)
            canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            canvas.mpl_connect("resize_event", lambda ev, f=fig: fit_titles(f))
            self.col.addWidget(canvas, 1)
        self._figs = list(figs)
        self._stack.setCurrentWidget(self.scroll)
        if self._pop is not None and self._pop.isVisible():
            self._refresh_pop()

    def save_png(self, parent=None):
        if not self._figs:
            return None
        path, _ = QFileDialog.getSaveFileName(parent or self, "Save plot", "half_life_hacker_plot.png", "PNG image (*.png)")
        if path:
            self._figs[0].savefig(path, dpi=200)
        return path
