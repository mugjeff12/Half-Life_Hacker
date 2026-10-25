"""Built-in self-test:  HalfLifeHacker --selftest [--shots DIR]
Drives the real UI headlessly: opens every step, loads the solution, runs it, checks the verdict."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from .content import ALL_STEPS


SIZE = (1520, 920)


def _expect(label, got, want, fails):
    ok = got == want
    print(f"{'PASS' if ok else 'FAIL'}  [negative] {label}: {got!r}" + ("" if ok else f"  (wanted {want!r})"))
    if not ok:
        fails.append(label)


def negative_tests(win, shots) -> list:
    """Unfinished / wrong / crashing code must give the right feedback (and never mark a step done)."""
    app = QApplication.instance()
    fails = []
    idx = {s.id: i for i, s in enumerate(ALL_STEPS)}

    def view(step_id):
        win.go(idx[step_id])
        app.processEvents()
        return win.current_view()

    v = view("s1-lambda")
    v.run()
    _expect("starter code (None) -> pending", v.state, "pending", fails)
    v.editor.setPlainText("lambda_I = 1.0\nlambda_Xe = 1.0\ncheck('lambda_I', lambda_I, 2.9306e-5, hint='np.log(2) / t_half_I')\n")
    v.run()
    _expect("wrong value -> bad", v.state, "bad", fails)
    _expect("wrong value does not tick the step", "s1-lambda" in win.ctx.progress.done, False, fails)
    if shots:
        QTest.qWait(100)
        win.grab().save(str(Path(shots) / "neg_wrong_answer.png"))
    v.editor.setPlainText("lambda_I = np.log(2) / t_half_I\nlambda_Xe = oops\n")
    v.run()
    _expect("NameError -> error", v.state, "error", fails)
    v.editor.setPlainText("lambda_I = (np.log(2) / t_half_I\n")
    v.run()
    _expect("SyntaxError -> error", v.state, "error", fails)
    v.reset_code()
    for _ in range(4):
        v.show_hint()
    _expect("hint ladder stops at the last hint", v._hint_level, len(ALL_STEPS[idx["s1-lambda"]].hints), fails)

    # a sim step run before its prerequisites -> friendly warning, not a crash
    win.ctx.session.reset()
    v = view("s1-sim")
    v.run()
    _expect("sim before prerequisites -> warn", v.state, "warn", fails)

    # xenon equations missing the absorption term -> bad, with hint
    for sid in ("s1-lambda", "s1-rate"):
        v = view(sid)
        v.editor.setPlainText(ALL_STEPS[idx[sid]].solution)
        v.run()
    v = view("s3-xenon")
    wrong = ALL_STEPS[idx["s3-xenon"]].solution.replace(" - sigma_a_Xe * Phi * N_Xe", "")
    v.editor.setPlainText(wrong)
    v.run()
    _expect("xenon eq. without absorption term -> bad", v.state, "bad", fails)
    if shots:
        QTest.qWait(100)
        win.grab().save(str(Path(shots) / "neg_missing_absorption.png"))

    # reveal while the reactor never shuts down -> warn
    for sid in ("s1-lambda", "s1-rate", "s3-pick", "s3-xenon", "s3-eq", "s3-scram"):
        st = ALL_STEPS[idx[sid]]
        v = view(sid)
        v.editor.setPlainText(st.solution or st.code)
        v.run()
    v = view("s3-scram")
    v.reset_code()
    v.run()
    _expect("shutdown_time still inf -> pending", v.state, "pending", fails)
    v = view("s3-reveal")
    v.run()
    _expect("reveal with no SCRAM -> warn", v.state, "warn", fails)

    # progress persistence round-trip
    import tempfile
    from .state import Progress
    with tempfile.TemporaryDirectory() as d:
        pr = Progress(Path(d) / "p.json")
        pr.code["x"] = "abc é 🔧"
        pr.done.add("x")
        pr.extras["prediction"] = "C"
        pr.save()
        pr2 = Progress(Path(d) / "p.json")
        _expect("progress round-trip", (pr2.code, pr2.done, pr2.extras), (pr.code, pr.done, pr.extras), fails)
    # export is runnable python
    import ast
    import os
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "export.py")
        win.write_export(out)
        ast.parse(open(out, encoding="utf-8").read())
        print("PASS  [negative] exported code is valid Python")
    return fails


def run(win, shots: str | None = None, size=None) -> int:
    global SIZE
    SIZE = size or SIZE
    app = QApplication.instance()
    if shots:
        Path(shots).mkdir(parents=True, exist_ok=True)
    win.resize(*SIZE)
    win.show()
    app.processEvents()
    bad = negative_tests(win, shots)
    win.ctx.progress.done.clear()
    win.ctx.session.reset()
    win.ctx.progress.extras.clear()
    win.ctx.progress.code.clear()
    for v in list(win.views.values()):
        win.stack.removeWidget(v)
        v.deleteLater()
    win.views.clear()
    print()
    for i, st in enumerate(ALL_STEPS):
        win.go(i)
        app.processEvents()
        v = win.current_view()
        if st.kind in ("code", "sim", "slider"):
            if st.solution:
                v.editor.setPlainText(st.solution)
            v.run()
            app.processEvents()
            ok = v.state == "ok"
            if st.kind == "slider":
                v.slider.setValue(v.slider.value() + 7)   # drag the slider a bit; debounce timer must redraw
                QTest.qWait(400)
                ok = ok and v.plot._figs != [] and v.plot._stack.currentWidget() is v.plot.scroll
        elif st.kind == "predict":
            v.radios["C"].setChecked(True)
            v._lock_prediction()
            ok = st.id in win.ctx.progress.done
        else:
            ok = True
        print(f"{'PASS' if ok else 'FAIL'}  {i + 1:>2}/{len(ALL_STEPS)}  {st.label or '-':>4}  {st.title}")
        if not ok:
            bad.append(st.id)
        if shots:
            QTest.qWait(120)
            win.grab().save(str(Path(shots) / f"{i + 1:02d}_{st.id}.png"))
    done = win.ctx.progress.done
    inter = [s for s in ALL_STEPS if s.kind in ("code", "sim", "slider", "predict")]
    missing = [s.id for s in inter if s.id not in done]
    print(f"\nactivities complete: {len(inter) - len(missing)}/{len(inter)}   failures: {bad or 'none'}")
    return 0 if not bad and not missing else 1
