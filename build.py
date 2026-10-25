#!/usr/bin/env python3
"""Build the Half-Life Hacker executable with PyInstaller.

    python build.py              # folder build (fast start-up) + zip         -> dist/HalfLifeHacker-<os>.zip
    python build.py --onefile    # single-file .exe (slower first start)       -> dist/HalfLifeHacker(.exe)
    python build.py --test       # also run the built app's self-test (opens every step, runs every solution)

PyInstaller cannot cross-compile: run this on Windows to get a .exe, on macOS to get a .app, on Linux for a Linux binary.
(Or let GitHub Actions do all three — see .github/workflows/build.yml.)
"""
import argparse
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NAME = "HalfLifeHacker"

# Qt modules the app never touches — leaving them out keeps the download much smaller.
EXCLUDES = [
    "tkinter", "PyQt5", "PyQt6", "PySide2",
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick", "PySide6.QtWebChannel",
    "PySide6.QtQuick", "PySide6.QtQuickWidgets", "PySide6.QtQuick3D", "PySide6.QtQml", "PySide6.Qt3DCore",
    "PySide6.Qt3DRender", "PySide6.Qt3DInput", "PySide6.Qt3DLogic", "PySide6.Qt3DAnimation", "PySide6.Qt3DExtras",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets", "PySide6.QtCharts", "PySide6.QtDataVisualization",
    "PySide6.QtPdf", "PySide6.QtPdfWidgets", "PySide6.QtSql", "PySide6.QtBluetooth", "PySide6.QtNfc",
    "PySide6.QtSensors", "PySide6.QtSerialPort", "PySide6.QtLocation", "PySide6.QtPositioning",
    "PySide6.QtRemoteObjects", "PySide6.QtScxml", "PySide6.QtStateMachine", "PySide6.QtSpatialAudio",
    "PySide6.QtHttpServer", "PySide6.QtTextToSpeech", "PySide6.QtGraphs", "IPython", "jupyter", "notebook", "pytest",
    # big scientific packages that may live in the builder's Python but are never used by this app
    "pandas", "lxml", "sympy", "numba", "h5py", "tables", "openpyxl", "xlrd", "bokeh", "plotly", "sklearn", "torch",
    "tensorflow", "cv2", "dask", "pyarrow", "statsmodels", "seaborn", "xarray", "sphinx", "docutils", "setuptools",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--onefile", action="store_true", help="single-file executable (Windows/Linux)")
    ap.add_argument("--test", action="store_true", help="run the built app's --selftest afterwards")
    ap.add_argument("--no-zip", action="store_true")
    a = ap.parse_args()

    try:
        import PyInstaller.__main__ as pyi
    except ImportError:
        sys.exit("PyInstaller is not installed:  pip install pyinstaller")

    system = platform.system()
    onefile = a.onefile and system != "Darwin"          # macOS apps are always folder bundles
    icon = ROOT / "assets" / ("naygn.ico" if system == "Windows" else "naygn.icns" if system == "Darwin" else "naygn_logo.png")

    for d in ("build", "dist"):
        shutil.rmtree(ROOT / d, ignore_errors=True)

    args = [
        str(ROOT / "main.py"), "--name", NAME, "--noconfirm", "--clean", "--windowed",
        "--onefile" if onefile else "--onedir",
        "--add-data", f"{ROOT / 'assets'}{os.pathsep}assets",
        "--hidden-import", "matplotlib.backends.backend_qtagg",
        "--hidden-import", "matplotlib.backends.backend_agg",
        "--collect-submodules", "scipy.integrate",
        "--collect-submodules", "scipy.special",
        "--distpath", str(ROOT / "dist"), "--workpath", str(ROOT / "build"), "--specpath", str(ROOT / "build"),
    ]
    if icon.exists() and system in ("Windows", "Darwin"):
        args += ["--icon", str(icon)]
    if system == "Darwin":
        args += ["--osx-bundle-identifier", "ca.naygn.mcmaster.halflifehacker"]
    for m in EXCLUDES:
        args += ["--exclude-module", m]
    print("PyInstaller", " ".join(args[:6]), "...")
    pyi.run(args)

    # locate the product
    if system == "Darwin":
        product = ROOT / "dist" / f"{NAME}.app"
        exe = product / "Contents" / "MacOS" / NAME
    elif onefile:
        product = exe = ROOT / "dist" / (NAME + (".exe" if system == "Windows" else ""))
    else:
        product = ROOT / "dist" / NAME
        exe = product / (NAME + (".exe" if system == "Windows" else ""))
    if not exe.exists():
        sys.exit(f"build finished but {exe} was not found")

    if a.test:
        print("\nRunning the built app's self-test …")
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
        log = Path(tempfile.gettempdir()) / "hlh_selftest.log"
        log.unlink(missing_ok=True)
        r = subprocess.run([str(exe), "--selftest"], env=env, timeout=900)
        if log.exists():                      # windowed Windows exe has no console: its results go to this file
            print(log.read_text(encoding="utf-8", errors="replace"))
        if r.returncode != 0:
            sys.exit("SELF-TEST FAILED (exit code %d)" % r.returncode)
        print("self-test passed ✓")

    if not onefile and not a.no_zip:
        tag = {"Windows": "Windows", "Darwin": "macOS", "Linux": "Linux"}.get(system, system)
        if system == "Darwin":
            # shutil's zip drops symlinks + the executable bit, which breaks a .app; ditto keeps them
            archive = str(ROOT / "dist" / f"{NAME}-{tag}.zip")
            subprocess.run(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", str(product), archive], check=True)
        else:
            archive = shutil.make_archive(str(ROOT / "dist" / f"{NAME}-{tag}"), "zip", root_dir=product.parent, base_dir=product.name)
        print("zip:", archive)
    size = sum(f.stat().st_size for f in product.rglob("*") if f.is_file()) if product.is_dir() else product.stat().st_size
    print(f"\nDone → {product}   ({size / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()
