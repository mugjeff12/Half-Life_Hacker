"""NAYGN brand palette (black / white / dark pink #7E0237) + Qt stylesheet + plot style."""

# --- brand palette -----------------------------------------------------------
MAROON = "#7E0237"        # NAYGN "dark pink"
MAROON_HI = "#A3194F"     # hover / lighter tint
MAROON_LO = "#5A0127"     # pressed
MAROON_TINT = "#F4E4EB"   # very light tint for callouts on white
BLACK = "#0B0B0B"
CHARCOAL = "#161616"
GRAPHITE = "#232323"
EDGE = "#2F2F2F"
WHITE = "#FFFFFF"
OFFWHITE = "#F7F5F6"
INK = "#1B1B1B"
MUTED = "#6B6B6B"
LINE = "#E3DDE0"
GREY = "#8C8C8C"

# semantic accents used sparingly in feedback only
OK_GREEN = "#7BD389"
BAD_ROSE = "#FF7A9E"
WARN_AMBER = "#F2C94C"

# --- editor syntax colours (on CHARCOAL) -------------------------------------
SYN = {
    "text": "#E8E8E8", "keyword": "#FF5C93", "builtin": "#FFB3CC", "defname": "#FFFFFF",
    "number": "#8FD0E0", "string": "#E5D3A1", "comment": "#7D7D7D", "todo": "#FF8FB3",
}

UI_FONTS = '"Segoe UI", "SF Pro Text", "Helvetica Neue", "Inter", "Noto Sans", "DejaVu Sans", sans-serif'
MONO_FONTS = ["Cascadia Mono", "Consolas", "Menlo", "DejaVu Sans Mono", "Liberation Mono", "Courier New"]


def qss() -> str:
    return f"""
* {{ font-family: {UI_FONTS}; }}
QWidget {{ font-size: 10.5pt; color: {INK}; }}
QMainWindow, #central {{ background: {OFFWHITE}; }}
QToolTip {{ background: {BLACK}; color: {WHITE}; border: 1px solid {MAROON}; padding: 4px; }}

/* ---------- header ---------- */
#header {{ background: {BLACK}; border-bottom: 3px solid {MAROON}; }}
#appTitle {{ color: {WHITE}; font-size: 17pt; font-weight: 700; }}
#appSub {{ color: #B9B9B9; font-size: 9.5pt; }}
#progressText {{ color: #D5D5D5; font-size: 9.5pt; }}
QProgressBar {{ background: {GRAPHITE}; border: none; border-radius: 4px; height: 8px; text-align: center; }}
QProgressBar::chunk {{ background: {MAROON_HI}; border-radius: 4px; }}

/* ---------- sidebar ---------- */
QTreeWidget#sidebar {{ background: {CHARCOAL}; border: none; color: #D8D8D8; outline: 0; padding: 6px 0; }}
QTreeWidget#sidebar::item {{ padding: 6px 8px; border-left: 3px solid transparent; }}
QTreeWidget#sidebar::item:hover {{ background: {GRAPHITE}; }}
QTreeWidget#sidebar::item:selected {{ background: {MAROON}; color: {WHITE}; border-left: 3px solid {WHITE}; }}
QTreeWidget#sidebar::branch {{ background: {CHARCOAL}; }}
QTreeWidget#sidebar::branch:selected {{ background: {CHARCOAL}; }}

/* ---------- footer nav ---------- */
#navbar {{ background: {WHITE}; border-top: 1px solid {LINE}; }}
#stepCounter {{ color: {MUTED}; }}

/* ---------- buttons ---------- */
QPushButton {{ background: {WHITE}; border: 1px solid #CFC6CA; border-radius: 6px; padding: 7px 16px; }}
QPushButton:hover {{ border-color: {MAROON}; color: {MAROON}; }}
QPushButton:disabled {{ color: #A9A9A9; background: #F0EDEE; border-color: {LINE}; }}
QPushButton#primary {{ background: {MAROON}; color: {WHITE}; border: 1px solid {MAROON}; font-weight: 600; }}
QPushButton#primary:hover {{ background: {MAROON_HI}; border-color: {MAROON_HI}; color: {WHITE}; }}
QPushButton#primary:pressed {{ background: {MAROON_LO}; }}
QPushButton#primary:disabled {{ background: #CDB3BF; border-color: #CDB3BF; color: {WHITE}; }}
QPushButton#glow {{ background: {MAROON}; color: {WHITE}; border: 2px solid {WHITE}; font-weight: 700; }}
QPushButton#glow:hover {{ background: {MAROON_HI}; color: {WHITE}; }}

/* toolbar buttons that sit on dark surfaces */
QPushButton#dark {{ background: {GRAPHITE}; color: #E8E8E8; border: 1px solid {EDGE}; padding: 6px 12px; }}
QPushButton#dark:hover {{ border-color: {MAROON_HI}; color: {WHITE}; }}
QPushButton#dark:disabled {{ color: #6A6A6A; }}
QPushButton#run {{ background: {MAROON}; color: {WHITE}; border: 1px solid {MAROON_HI}; font-weight: 700; padding: 6px 16px; }}
QPushButton#run:hover {{ background: {MAROON_HI}; }}

/* ---------- code + console ---------- */
#editorCard, #consoleCard {{ background: {CHARCOAL}; border: 1px solid {EDGE}; border-radius: 8px; }}
#editorBar {{ background: {GRAPHITE}; border-top-left-radius: 8px; border-top-right-radius: 8px; border-bottom: 1px solid {EDGE}; }}
#editorTitle, #consoleTitle {{ color: #CFCFCF; font-weight: 600; font-size: 9.5pt; }}
QPlainTextEdit {{ background: {CHARCOAL}; color: {SYN['text']}; border: none; selection-background-color: {MAROON}; selection-color: {WHITE}; }}
#chip {{ border-radius: 10px; padding: 3px 12px; font-weight: 600; font-size: 9.5pt; background: {EDGE}; color: #D0D0D0; }}
#chip[state="ok"] {{ background: #1F3B27; color: {OK_GREEN}; }}
#chip[state="bad"] {{ background: #4A1A2A; color: {BAD_ROSE}; }}
#chip[state="pending"] {{ background: #4A3D12; color: {WARN_AMBER}; }}

/* ---------- lesson text + plots ---------- */
QTextBrowser {{ background: {WHITE}; border: 1px solid {LINE}; border-radius: 8px; padding: 10px 14px; selection-background-color: {MAROON}; selection-color: {WHITE}; }}
#plotCard {{ background: {WHITE}; border: 1px solid {LINE}; border-radius: 8px; }}
QScrollArea {{ border: none; background: transparent; }}
#sliderBar {{ background: {WHITE}; border-bottom: 1px solid {LINE}; border-top-left-radius: 8px; border-top-right-radius: 8px; }}
#sliderValue {{ color: {MAROON}; font-weight: 700; font-size: 12pt; }}
QSlider::groove:horizontal {{ height: 6px; background: #E6DDE1; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: {MAROON}; border-radius: 3px; }}
QSlider::handle:horizontal {{ background: {WHITE}; border: 3px solid {MAROON}; width: 16px; height: 16px; margin: -7px 0; border-radius: 9px; }}
QRadioButton {{ padding: 8px 6px; spacing: 10px; }}
QRadioButton::indicator {{ width: 16px; height: 16px; }}

QSplitter::handle {{ background: transparent; }}
QSplitter::handle:hover {{ background: #D9C6CF; border-radius: 3px; }}
QSplitter::handle:horizontal {{ width: 10px; }}
QSplitter::handle:vertical {{ height: 10px; }}
QMenuBar {{ background: {BLACK}; color: #E0E0E0; }}
QMenuBar::item:selected {{ background: {MAROON}; }}
QMenu {{ background: {WHITE}; border: 1px solid {LINE}; }}
QMenu::item:selected {{ background: {MAROON}; color: {WHITE}; }}
QStatusBar {{ background: {BLACK}; color: #BEBEBE; }}
QScrollBar:vertical {{ background: transparent; width: 12px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #BDB1B7; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {MAROON}; }}
QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: #BDB1B7; border-radius: 4px; min-width: 30px; }}
QScrollBar::handle:horizontal:hover {{ background: {MAROON}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
"""


def apply_mpl_style():
    """White plot cards with the brand colour cycle (C0 burgundy, C1 charcoal, C2 grey, C3 burgundy)."""
    import matplotlib as mpl
    from cycler import cycler
    mpl.rcParams.update({
        "axes.prop_cycle": cycler(color=[MAROON, "#1A1A1A", GREY, MAROON, "#C2527F", "#4D4D4D"]),
        "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
        "axes.edgecolor": "#B9B0B4", "axes.labelcolor": INK, "text.color": INK,
        "xtick.color": "#4A4A4A", "ytick.color": "#4A4A4A",
        "axes.titleweight": "bold", "axes.titlecolor": INK,
        "grid.color": "#CFC6CA", "axes.spines.top": False, "axes.spines.right": False,
        "legend.frameon": True, "legend.framealpha": 0.92, "legend.edgecolor": "#D8D0D4",
    })
