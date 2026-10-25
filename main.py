"""Half-Life Hacker — NAYGN McMaster workshop app.   Run:  python main.py      Self-test:  python main.py --selftest"""
import os
import sys

os.environ.setdefault("QT_API", "pyside6")


SELFTEST_LOG = os.path.join(__import__("tempfile").gettempdir(), "hlh_selftest.log")


def _safe_streams(selftest: bool):
    """Windowed (no-console) Windows builds have sys.stdout = None, and piped Windows consoles are cp1252:
    printing '✓' or '–' then raises. Make both streams safe; in --selftest mode keep a log file instead."""
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name)
        if stream is None:
            sink = open(SELFTEST_LOG if selftest else os.devnull, "w", encoding="utf-8")
            setattr(sys, name, sink)
        else:
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def main() -> int:
    args = sys.argv[1:]
    selftest = "--selftest" in args
    _safe_streams(selftest)
    if selftest and "QT_QPA_PLATFORM" not in os.environ and sys.platform.startswith("linux"):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"

    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QFont, QFontDatabase, QPainter, QPixmap
    from PySide6.QtWidgets import QApplication, QSplashScreen

    app = QApplication(sys.argv)
    app.setOrganizationName("NAYGN McMaster")
    app.setApplicationName("Half-Life Hacker")
    app.setApplicationDisplayName("Half-Life Hacker")

    from hlh import theme
    from hlh.paths import asset
    app.setStyleSheet(theme.qss())

    # bundled fonts (keeps the app looking identical on every OS; DejaVu ships with matplotlib)
    try:
        import matplotlib
        fdir = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")
        for fn in ("DejaVuSansMono.ttf", "DejaVuSansMono-Bold.ttf", "DejaVuSans.ttf", "DejaVuSans-Bold.ttf"):
            p = os.path.join(fdir, fn)
            if os.path.exists(p):
                QFontDatabase.addApplicationFont(p)
    except Exception:
        pass

    # splash while scipy / matplotlib load
    splash = None
    if not selftest:
        pm = QPixmap(460, 320)
        pm.fill(QColor(theme.BLACK))
        p = QPainter(pm)
        p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        logo = QPixmap(str(asset("naygn_logo.png"))).scaled(170, 170, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        p.drawPixmap((460 - 170) // 2, 28, logo)
        p.fillRect(0, 312, 460, 8, QColor(theme.MAROON))
        f = QFont(app.font())
        f.setPointSizeF(15)
        f.setBold(True)
        f.setLetterSpacing(QFont.AbsoluteSpacing, 3)
        p.setFont(f)
        p.setPen(QColor("white"))
        p.drawText(0, 218, 460, 30, Qt.AlignCenter, "HALF-LIFE HACKER")
        f.setPointSizeF(9.5)
        f.setBold(False)
        p.setFont(f)
        p.setPen(QColor("#FF8FB3"))
        p.drawText(0, 252, 460, 24, Qt.AlignCenter, "Loading the physics engine…")
        p.end()
        splash = QSplashScreen(pm)
        splash.show()
        app.processEvents()

    from hlh.mainwindow import MainWindow
    from hlh.session import Session
    from hlh.state import AppContext, Progress, default_progress_path

    prog = Progress(None if selftest else default_progress_path())
    ctx = AppContext(Session(), prog)
    win = MainWindow(ctx)

    if selftest:
        from hlh import selftest as st
        shots = args[args.index("--shots") + 1] if "--shots" in args else None
        size = tuple(int(x) for x in args[args.index("--size") + 1].split("x")) if "--size" in args else None
        return st.run(win, shots, size)

    win.show()
    if splash:
        splash.finish(win)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
