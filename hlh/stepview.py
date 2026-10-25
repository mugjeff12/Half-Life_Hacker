"""One page of the workshop: lesson text on the left, a live coding workspace on the right."""
from __future__ import annotations

import html
import re

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QButtonGroup, QFrame, QHBoxLayout, QLabel, QMessageBox, QPushButton,
                               QRadioButton, QSizePolicy, QSlider, QSplitter, QVBoxLayout, QWidget)

from . import theme
from .config import SOLUTIONS_ENABLED
from .content import Section, Step
from .editor import CodeEditor
from .physics_ref import HOUR
from .state import AppContext
from .widgets import BannerLabel, OutputConsole, PlotPanel, RichView


def _plain(h: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", h))


def _frame(name: str) -> QFrame:
    f = QFrame()
    f.setObjectName(name)
    return f


class StepView(QWidget):
    completed = Signal(str, bool)

    def __init__(self, step: Step, section: Section, sec_index: int, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.step, self.section, self.sec_index, self.ctx = step, section, sec_index, ctx
        self.session = ctx.session
        self.editor: CodeEditor | None = None
        self.console: OutputConsole | None = None
        self.plot: PlotPanel | None = None
        self._hint_level = 0
        self._auto_done = False
        self._slider_timer = QTimer(self)
        self._slider_timer.setSingleShot(True)
        self._slider_timer.timeout.connect(self._render_slider)
        self.has_plot = step.kind == "slider" or (step.kind == "sim" and "plt.show()" in step.code)
        self.state = "none"

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 8)
        root.setSpacing(10)
        if step is section.steps[0]:
            root.addWidget(self._banner())

        self.rich = RichView(step.html)
        k = step.kind
        if k in ("info", "predict", "final"):
            col = QWidget()
            colv = QVBoxLayout(col)
            colv.setContentsMargins(0, 0, 0, 0)
            colv.addWidget(self.rich, 1)
            if k == "predict":
                self.rich.setMaximumHeight(250)
                colv.addWidget(self._build_predict())
                colv.addStretch(1)
            if k == "final":
                self.summary = QLabel()
                self.summary.setWordWrap(True)
                self.summary.setTextFormat(Qt.RichText)
                colv.addWidget(self.summary)
                colv.addWidget(self._build_final_buttons())
            row = QHBoxLayout()
            row.addStretch(1)
            col.setMaximumWidth(980)
            row.addWidget(col, 100)
            row.addStretch(1)
            root.addLayout(row, 1)
        else:
            split = QSplitter(Qt.Horizontal)
            split.setChildrenCollapsible(False)
            split.addWidget(self.rich)
            split.addWidget(self._build_workspace())
            split.setStretchFactor(0, 4)
            split.setStretchFactor(1, 7)
            split.setSizes([380, 800] if k in ('sim', 'slider') else [430, 750])
            root.addWidget(split, 1)
        self.rich.set_zoom(ctx.text_zoom)
        if step.kind in ('code', 'sim', 'slider'):
            self.rich.setMinimumWidth(300)

    # ------------------------------------------------------------------ banner
    def _banner(self) -> QWidget:
        s, sec = self.step, self.section
        if sec.id == "welcome":
            kicker, title = "NAYGN McMaster · Workshop", "Half-Life Hacker"
        elif sec.id == "finish":
            kicker, title = "Mission complete", "Wrap-up"
        else:
            kicker, title = sec.rung, sec.title
        return BannerLabel(sec.banner, sec.focus, kicker, title)

    # ------------------------------------------------------------------ workspace (code / sim / slider)
    def _build_workspace(self) -> QWidget:
        st = self.step
        self.split = QSplitter(Qt.Vertical)
        self.split.setChildrenCollapsible(False)
        self.split.setMinimumWidth(460)

        # editor card ----------------------------------------------------------
        self.editor_card = _frame("editorCard")
        ev = QVBoxLayout(self.editor_card)
        ev.setContentsMargins(0, 0, 0, 0)
        ev.setSpacing(0)
        bar = _frame("editorBar")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(12, 7, 10, 7)
        title = QLabel("✏️  Your code" if st.solution else "📖  Given code — read it, tinker if you like")
        title.setObjectName("editorTitle")
        bl.addWidget(title)
        self.chip = QLabel("Ready")
        self.chip.setObjectName("chip")
        bl.addWidget(self.chip)
        bl.addStretch(1)
        self.hint_btn = QPushButton("💡 Hint")
        self.sol_btn = QPushButton("👁 Solution")
        self.reset_btn = QPushButton("↺ Reset")
        self.hide_btn = QPushButton("Hide code")
        self.run_btn = QPushButton("▶  Run")
        for b in (self.hint_btn, self.sol_btn, self.reset_btn, self.hide_btn):
            b.setObjectName("dark")
        self.run_btn.setObjectName("run")
        self.run_btn.setToolTip("Run (Ctrl+Enter)")
        if st.solution:
            bl.addWidget(self.hint_btn)
            if SOLUTIONS_ENABLED:
                bl.addWidget(self.sol_btn)
            else:
                self.sol_btn.hide()
        else:
            self.hint_btn.hide()
            self.sol_btn.hide()
        bl.addWidget(self.reset_btn)
        if st.kind in ("sim", "slider"):
            bl.addWidget(self.hide_btn)
        else:
            self.hide_btn.hide()
        bl.addWidget(self.run_btn)
        ev.addWidget(bar)
        self.editor = CodeEditor(todo_mode=bool(st.solution))
        self.editor.set_point_size(self.ctx.editor_pt)
        self.editor.setPlainText(self.ctx.progress.code.get(st.id, st.code))
        ev.addWidget(self.editor, 1)
        self.split.addWidget(self.editor_card)

        # plot card ------------------------------------------------------------
        self.plot_card = _frame("plotCard")
        pv = QVBoxLayout(self.plot_card)
        pv.setContentsMargins(0, 0, 0, 0)
        pv.setSpacing(0)
        if st.kind == "slider":
            pv.addWidget(self._build_slider_bar())
        self.plot = PlotPanel()
        pv.addWidget(self.plot, 1)
        self.plot.set_title(st.title)
        save = QPushButton("💾 Save plot as PNG")
        save.setStyleSheet("margin: 4px 8px 6px 8px; padding: 4px 12px; font-size: 9.5pt;")
        save.clicked.connect(lambda: self.plot.save_png(self))
        expand = QPushButton("⤢ Expand plot")
        expand.setToolTip("Open the plot in its own big window (Ctrl+E) — zoom, pan and save from there")
        expand.setStyleSheet("margin: 4px 0px 6px 8px; padding: 4px 12px; font-size: 9.5pt;")
        expand.clicked.connect(self.plot.pop_out)
        QShortcut(QKeySequence("Ctrl+E"), self, activated=self._expand_shortcut)
        srow = QHBoxLayout()
        srow.setContentsMargins(0, 0, 0, 0)
        srow.addStretch(1)
        srow.addWidget(expand)
        srow.addWidget(save)
        pv.addLayout(srow)
        self.split.addWidget(self.plot_card)
        self.plot_card.setVisible(self.has_plot)

        # console card ---------------------------------------------------------
        self.console_card = _frame("consoleCard")
        cv = QVBoxLayout(self.console_card)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(0)
        ct = QLabel("  Console")
        ct.setObjectName("consoleTitle")
        ct.setStyleSheet("padding: 6px 4px;")
        cv.addWidget(ct)
        self.console = OutputConsole()
        self.console.set_point_size(max(9.5, self.ctx.editor_pt - 1))
        cv.addWidget(self.console, 1)
        self.split.addWidget(self.console_card)

        self.split.setStretchFactor(0, 5 if self.has_plot else 4)
        self.split.setStretchFactor(1, 7)
        self.split.setStretchFactor(2, 2 if self.has_plot else 3)

        self.run_btn.clicked.connect(self.run)
        self.reset_btn.clicked.connect(self.reset_code)
        self.hint_btn.clicked.connect(self.show_hint)
        self.sol_btn.clicked.connect(self.show_solution)
        self.hide_btn.clicked.connect(self._toggle_code)
        self.editor.run_requested.connect(self.run)
        self.editor.textChanged.connect(self._on_edit)
        return self.split

    def _build_slider_bar(self) -> QWidget:
        sl = self.step.slider
        bar = _frame("sliderBar")
        v = QVBoxLayout(bar)
        v.setContentsMargins(14, 8, 14, 8)
        v.setSpacing(4)
        top = QHBoxLayout()
        top.addWidget(QLabel(f"<b>{sl['label']}</b>"))
        top.addStretch(1)
        self.slider_val = QLabel()
        self.slider_val.setObjectName("sliderValue")
        top.addWidget(self.slider_val)
        v.addLayout(top)
        row = QHBoxLayout()
        row.setSpacing(8)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(round(sl["lo"] * 10), round(sl["hi"] * 10))
        self.slider.setValue(round(sl["value"] * 10))
        self.slider.setMinimumWidth(160)
        row.addWidget(self.slider, 1)
        for name, val in sl["presets"]:
            b = QPushButton(name)
            b.setStyleSheet("padding: 3px 9px; font-size: 9pt;")
            b.clicked.connect(lambda _=False, val=val: self.slider.setValue(round(val * 10)))
            row.addWidget(b)
        v.addLayout(row)
        self.slider.valueChanged.connect(self._on_slider)
        self._update_slider_label()
        return bar

    def _slider_value(self) -> float:
        return self.slider.value() / 10.0

    def _update_slider_label(self):
        self.slider_val.setText(f"{self._slider_value():.1f} {self.step.slider['unit']}")

    def _on_slider(self, _):
        self._update_slider_label()
        self._slider_timer.start(110)

    # ------------------------------------------------------------------ predict / final extras
    def _build_predict(self) -> QWidget:
        w = _frame("plotCard")
        v = QVBoxLayout(w)
        v.setContentsMargins(16, 10, 16, 12)
        self.group = QButtonGroup(self)
        self.radios = {}
        for key, text in self.step.options:
            rb = QRadioButton(f"({key})   {text}")
            rb.setStyleSheet("font-size: 11.5pt;")
            self.group.addButton(rb)
            self.radios[key] = rb
            v.addWidget(rb)
        row = QHBoxLayout()
        self.lock_btn = QPushButton("🔒  Lock in our prediction")
        self.lock_btn.setObjectName("primary")
        self.lock_btn.clicked.connect(self._lock_prediction)
        self.lock_lbl = QLabel("")
        self.lock_lbl.setStyleSheet(f"color:{theme.MAROON}; font-weight:600;")
        row.addWidget(self.lock_btn)
        row.addWidget(self.lock_lbl, 1)
        v.addLayout(row)
        guess = self.ctx.progress.extras.get("prediction")
        if guess in self.radios:
            self.radios[guess].setChecked(True)
            self._set_locked(guess)
        return w

    def _lock_prediction(self):
        for key, rb in self.radios.items():
            if rb.isChecked():
                self.ctx.progress.extras["prediction"] = key
                self.ctx.save_soon()
                self._set_locked(key)
                self.ctx.mark(self.step.id, True)
                self.completed.emit(self.step.id, True)
                return
        QMessageBox.information(self, "Pick one first", "Choose A, B or C before locking in your team's prediction.")

    def _set_locked(self, key):
        for rb in self.radios.values():
            rb.setEnabled(False)
        self.lock_btn.setEnabled(False)
        self.lock_lbl.setText(f"Locked in: ({key}).  Now carry on — the next steps will reveal the answer!")

    def _build_final_buttons(self) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 4, 0, 0)
        self.export_btn = QPushButton("💾  Export my code (.py)")
        self.export_btn.setObjectName("primary")
        h.addWidget(self.export_btn)
        h.addStretch(1)
        return w

    def refresh_final(self, secs, all_steps):
        done = self.ctx.progress.done
        rows = []
        for i, sec in enumerate(secs):
            inter = [s for s in sec.steps if s.kind in ("code", "sim", "slider", "predict")]
            if not inter:
                continue
            n = sum(1 for s in inter if s.id in done)
            mark = "✓" if n == len(inter) else "○"
            rows.append(f"<tr><td>{mark}</td><td>&nbsp;{sec.title}</td><td align='right'>&nbsp;&nbsp;{n}/{len(inter)}</td></tr>")
        ns = self.session.ns
        facts = []
        try:
            ov, tp, sd = ns.get("overshoot"), ns.get("t_peak"), ns.get("sd_h")
            if ov is not None and tp is not None and sd is not None:
                facts.append(f"Your xenon peak: <b>{ov:.2f}×</b> its operating level, <b>{tp - sd:.1f} h</b> after shutdown.")
            f = ns.get("decay_heat_fraction")
            if f is not None:
                v = f(HOUR)
                if v is not None:
                    facts.append(f"Decay heat 1 hour after shutdown: <b>{v * 100:.2f}%</b> of full power.")
        except Exception:
            pass
        total = sum(1 for s in all_steps if s.kind in ("code", "sim", "slider", "predict"))
        got = sum(1 for s in all_steps if s.kind in ("code", "sim", "slider", "predict") and s.id in done)
        html_ = (f"<p style='font-size:11pt'><b>Your progress: {got} of {total} activities complete.</b></p>"
                 f"<table cellpadding='2'>{''.join(rows)}</table>")
        if facts:
            html_ += "<p style='font-size:11pt'>" + "<br>".join(facts) + "</p>"
        self.summary.setText(html_)

    # ------------------------------------------------------------------ behaviour
    def _apply_initial_sizes(self):
        if self.editor is None or getattr(self, "_sized", False):
            return
        h = self.split.height()
        if h < 200:
            return
        self._sized = True
        if self.has_plot:
            self.split.setSizes([int(h * 0.27), int(h * 0.55), int(h * 0.18)])
        else:
            self.split.setSizes([int(h * 0.58), 0, int(h * 0.42)])

    def showEvent(self, e):
        super().showEvent(e)
        QTimer.singleShot(0, self._apply_initial_sizes)
        if self.step.kind == "final":
            from .content import ALL_STEPS, SECTIONS
            self.refresh_final(SECTIONS, ALL_STEPS)
        if self.step.autorun and not self._auto_done and self.editor is not None:
            self._auto_done = True
            QTimer.singleShot(60, self.run)

    def _on_edit(self):
        self.ctx.progress.code[self.step.id] = self.editor.toPlainText()
        self.ctx.save_soon()

    def _expand_shortcut(self):
        if self.has_plot and self.plot is not None:
            self.plot.pop_out()

    def dispose(self):
        """Called when this page is thrown away (e.g. Reset all) so its big plot window doesn't linger."""
        if self.plot is not None:
            self.plot.close_pop()

    def _toggle_code(self):
        hide = self.editor.isVisible()
        self.editor.setVisible(not hide)
        self.hide_btn.setText("Show code" if hide else "Hide code")
        if hide:
            self.editor_card.setMaximumHeight(44)
        else:
            self.editor_card.setMaximumHeight(16777215)

    def reset_code(self):
        self.editor.setPlainText(self.step.code)
        self._hint_level = 0
        self._set_chip("none", "Reset to starter code")

    def show_hint(self):
        hints = self.step.hints
        if not hints:
            return
        n = len(hints)
        self._hint_level = min(self._hint_level + 1, n)
        self.console.add(f"💡 Hint {self._hint_level}/{n}: {_plain(hints[self._hint_level - 1])}", "hint")
        if self._hint_level == n:
            if SOLUTIONS_ENABLED:
                self.console.add("   (No more hints — 👁 Solution will fill in the answer if you want to compare.)", "info")
            else:
                self.console.add("   (No more hints — stuck? Ask a workshop leader or a neighbour.)", "info")

    def show_solution(self):
        if not SOLUTIONS_ENABLED:
            return
        r = QMessageBox.question(self, "Show the solution?",
                                 "Try the 💡 hints first — they're there to help you work it out.\n\n"
                                 "Replace your code with the solution? (↺ Reset brings back the starter code.)")
        if r == QMessageBox.Yes:
            self.editor.setPlainText(self.step.solution)
            self.console.add("👁 Solution loaded — press ▶ Run to see it pass.", "info")

    def _set_chip(self, state: str, text: str):
        self.chip.setText(text)
        self.chip.setProperty("state", state)
        self.chip.style().unpolish(self.chip)
        self.chip.style().polish(self.chip)

    # -- run ---------------------------------------------------------------------
    def run(self):
        if self.editor is None:
            return
        st = self.step
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.ctx.status.emit("Running…")
        QApplication.processEvents()
        try:
            res = self.session.run(self.editor.toPlainText(), f"<{st.id}>", after=st.after)
        finally:
            QApplication.restoreOverrideCursor()
        needs_earlier = (not res.ok) and (
            (res.error or "").startswith("⚠")
            or (st.kind in ("sim", "slider") and (res.exc_type == "NameError" or (res.exc_type == "TypeError" and "NoneType" in (res.error or "")))))
        self.console.clear()
        self.console.add_output(res.output)
        if res.error:
            self.console.add(("⚠ " if needs_earlier and not res.error.startswith("⚠") else "" if needs_earlier else "✗ ") + res.error,
                             "warn" if needs_earlier else "err")
            if res.error_line:
                self._mark_error_line(res.error_line)
        if res.ok and st.note:
            extra = st.note(self.session.ns, self.ctx.progress.extras)
            if extra:
                self.console.add("", "info")
                self.console.add(extra[0], extra[1])

        # verdict
        if not res.ok:
            state = "warn" if needs_earlier else "error"
        elif res.checks:
            state = "ok" if res.checks_ok else ("pending" if res.any_pending and not any(s == "bad" for _, s in res.checks) else "bad")
        else:
            state = "ok"
        if state == "ok" and st.done_if and not st.done_if(self.session.ns):
            state = "warn"
        texts = {"ok": "✓ Correct" if res.checks else "✓ Done", "bad": "✗ Not yet — see the console",
                 "pending": "⏳ Unfinished — fill in the TODO", "error": "✗ Error — see the console",
                 "warn": "⚠ Needs an earlier step / change"}
        self._set_chip("ok" if state == "ok" else "pending" if state in ("pending", "warn") else "bad", texts[state])
        self.state = state

        if self.has_plot:
            if st.kind == "slider":
                if state == "ok":
                    self._render_slider()
                else:
                    self.plot.show_message("This plot needs the earlier steps first — see the console.")
            else:
                if res.figures:
                    self.plot.set_figures(res.figures)
                elif state != "ok":
                    self.plot.show_message("Nothing to draw yet — read the message in the console, fix it, and press ▶ Run.")
        done = state == "ok"
        self.ctx.mark(st.id, done)
        self.completed.emit(st.id, done)
        self.ctx.status.emit("Ready")

    def _mark_error_line(self, line: int):
        # move the caret to the offending line so the student sees where to look
        blk = self.editor.document().findBlockByNumber(line - 1)
        if blk.isValid():
            cur = self.editor.textCursor()
            cur.setPosition(blk.position())
            self.editor.setTextCursor(cur)

    # -- sliders -----------------------------------------------------------------
    def _render_slider(self):
        if self.editor is None or self.step.kind != "slider":
            return
        sl = self.step.slider
        res = self.session.call(sl["func"], self._slider_value())
        if res.ok and res.figures:
            self.plot.set_figures(res.figures)
            self.ctx.mark(self.step.id, True)
            self.completed.emit(self.step.id, True)
        else:
            why = res.error or "nothing was drawn"
            self.plot.show_message(f"Can't draw this yet: {why}\n\nFinish the earlier steps (the equations you wrote) and come back.")

    # -- external controls ---------------------------------------------------------
    def apply_zoom(self):
        self.rich.set_zoom(self.ctx.text_zoom)
        if self.editor is not None:
            self.editor.set_point_size(self.ctx.editor_pt)
            self.console.set_point_size(max(9.5, self.ctx.editor_pt - 1))
