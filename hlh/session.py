"""The 'kernel': one persistent namespace shared by every step, exactly like running notebook cells top to bottom."""
from __future__ import annotations

import io
import traceback
import warnings
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field

import matplotlib

matplotlib.use("Agg")  # figures are drawn off-screen, then embedded in Qt canvases by the UI
import matplotlib.pyplot as plt  # noqa: E402

from . import theme  # noqa: E402
from .cells import CELLS  # noqa: E402

# Replaces the notebook's SETUP cell (the pip-install safety net isn't needed in an app).
# `check` is the notebook's helper, plus it *records* each verdict so the UI can tick the step off.
PRELUDE = '''\
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp

plt.rcParams.update({
    "figure.figsize": (9, 5.5),
    "axes.grid": True, "grid.alpha": 0.3,
    "font.size": 12, "axes.titlesize": 13, "lines.linewidth": 2.2,
})

__checks__ = []

def check(name, value, expected, tol=0.02, hint=""):
    if value is None:
        print(f"  ⏳ {name}: not done yet — replace `None` with your answer, then re-run.")
        __checks__.append((name, "pending"))
        return
    try:
        ok = abs(value - expected) <= tol * abs(expected)
    except Exception:
        ok = False
    if ok:
        print(f"  ✓ {name} looks right  (= {value:.4g})")
        __checks__.append((name, "ok"))
    else:
        print(f"  ✗ {name} = {value:.4g}, but I expected ≈ {expected:.4g}")
        __checks__.append((name, "bad"))
        if hint:
            print(f"     hint: {hint}")
'''


@dataclass
class RunResult:
    ok: bool = True                 # ran without an exception
    output: str = ""                # captured stdout/stderr
    error: str | None = None        # friendly error text
    error_line: int | None = None   # 1-based line in the student's code
    exc_type: str = ""              # e.g. 'NameError'
    checks: list = field(default_factory=list)   # [(name, 'ok'|'bad'|'pending')]
    figures: list = field(default_factory=list)

    @property
    def checks_ok(self) -> bool:
        return bool(self.checks) and all(s == "ok" for _, s in self.checks)

    @property
    def any_pending(self) -> bool:
        return any(s == "pending" for _, s in self.checks)


def _friendly(exc: BaseException, code: str, filename: str):
    """Turn a traceback into one short, kind message + the offending line number."""
    line_no = None
    tb = traceback.extract_tb(exc.__traceback__)
    for fr in reversed(tb):
        if fr.filename == filename:
            line_no = fr.lineno
            break
    if isinstance(exc, SyntaxError) and exc.filename == filename:
        line_no = exc.lineno

    name = type(exc).__name__
    msg = str(exc)
    if isinstance(exc, AssertionError) and msg:
        text = f"⚠ {msg}"
    elif isinstance(exc, SyntaxError):
        text = f"Syntax problem: {exc.msg}. Check brackets, colons and indentation."
    elif isinstance(exc, NameError):
        text = (f"{msg}. A step you skipped (or haven't run yet) creates this name — "
                f"run the earlier steps first.")
    elif isinstance(exc, TypeError) and "NoneType" in msg:
        text = (f"{name}: {msg}. A variable is still `None` — finish the 🔧 TODO in an earlier step "
                f"and press Run on it.")
    else:
        text = f"{name}: {msg}"
    if line_no is not None and not isinstance(exc, AssertionError):
        lines = code.splitlines()
        src = lines[line_no - 1].strip() if 0 < line_no <= len(lines) else ""
        text += f"\n   → line {line_no}: {src}"
    return text, line_no


class Session:
    def __init__(self):
        self.ns: dict = {}
        self.reset()

    # -- lifecycle ------------------------------------------------------------
    def reset(self):
        plt.close("all")
        self.ns = {"__name__": "__main__"}
        exec(compile(PRELUDE, "<prelude>", "exec"), self.ns)
        theme.apply_mpl_style()
        self.exec_quiet(CELLS["3acb2a6a"], "<data-table>")   # the physics data table, always loaded

    def exec_quiet(self, code: str, filename: str):
        with redirect_stdout(io.StringIO()), warnings.catch_warnings():
            warnings.simplefilter("ignore")
            exec(compile(code, filename, "exec"), self.ns)

    # -- running --------------------------------------------------------------
    def _collect_figs(self):
        return [plt.figure(n) for n in plt.get_fignums()]

    def run(self, code: str, filename: str = "<step>", after=None) -> RunResult:
        """Run student code, then (if it ran cleanly) the step's hidden `after(ns)` auto-check."""
        res = RunResult()
        plt.close("all")
        self.ns["__checks__"] = []
        theme.apply_mpl_style()
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(buf), warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                exec(compile(code, filename, "exec"), self.ns)
                if after is not None:
                    after(self.ns)
            except BaseException as exc:  # noqa: BLE001  (students can raise anything)
                if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                    raise
                res.ok = False
                res.exc_type = type(exc).__name__
                res.error, res.error_line = _friendly(exc, code, filename)
        res.output = buf.getvalue()
        res.checks = list(self.ns.get("__checks__", []))
        res.figures = self._collect_figs()
        return res

    def call(self, func_name: str, *args) -> RunResult:
        """Call a function defined by earlier code (used by the sliders) and capture its figure."""
        res = RunResult()
        plt.close("all")
        theme.apply_mpl_style()
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(buf), warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                self.ns[func_name](*args)
            except BaseException as exc:  # noqa: BLE001
                if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                    raise
                res.ok = False
                res.error = f"{type(exc).__name__}: {exc}"
        res.output = buf.getvalue()
        res.figures = self._collect_figs()
        return res
