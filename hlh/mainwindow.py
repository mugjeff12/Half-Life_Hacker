"""Main window: NAYGN header, step sidebar, lesson pages, navigation, menus."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (QFileDialog, QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QProgressBar,
                               QPushButton, QStackedWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from . import theme
from .content import ALL_STEPS, SECTIONS
from .paths import asset
from .session import PRELUDE
from .state import AppContext
from .stepview import StepView
from .widgets import pixmap

INTERACTIVE = ("code", "sim", "slider", "predict")
SHORT = {"welcome": "Welcome", "s1": "Rung 1 · Single isotope", "s2": "Rung 2 · Two-step chain",
         "s3": "Rung 3 · The reactor", "s4": "Rung 4 · Decay heat", "s5": "Rung 5 · Long-lived waste",
         "finish": "Wrap-up"}
VERSION = "1.0.0"


class MainWindow(QMainWindow):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self.setWindowTitle("Half-Life Hacker — NAYGN McMaster")
        self.setWindowIcon(self._icon())
        scr = self.screen().availableGeometry() if self.screen() else None
        w, h = (min(1520, int(scr.width() * 0.96)), min(920, int(scr.height() * 0.94))) if scr else (1520, 920)
        self.resize(w, h)
        self.setMinimumSize(900, 600)

        self.views: dict[str, StepView] = {}
        self.index_of = {st.id: i for i, st in enumerate(ALL_STEPS)}
        self.sec_of = {}
        for si, sec in enumerate(SECTIONS):
            for st in sec.steps:
                self.sec_of[st.id] = (sec, si)
        self.current = -1
        self._sidebar_user_set = False

        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        v = QVBoxLayout(central)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        v.addWidget(self._build_header())
        mid = QHBoxLayout()
        mid.setSpacing(0)
        self.tree = self._build_sidebar()
        mid.addWidget(self.tree)
        self.stack = QStackedWidget()
        mid.addWidget(self.stack, 1)
        v.addLayout(mid, 1)
        v.addWidget(self._build_navbar())

        self._build_menus()
        self.statusBar().showMessage("Ready")
        ctx.status.connect(self.statusBar().showMessage)
        ctx.progress_changed.connect(self.refresh_progress)
        QShortcut(QKeySequence("Alt+Right"), self, activated=self.next)
        QShortcut(QKeySequence("Alt+Left"), self, activated=self.back)
        QShortcut(QKeySequence("F5"), self, activated=self.run_current)
        QShortcut(QKeySequence("F11"), self, activated=self.toggle_fullscreen)

        last = self.index_of.get(ctx.progress.last, 0)
        self.go(last)
        self.refresh_progress()

    # ------------------------------------------------------------------ pieces
    def _icon(self):
        from PySide6.QtGui import QIcon
        return QIcon(str(asset("naygn_logo.png")))

    def _build_header(self) -> QWidget:
        h = QFrame()
        h.setObjectName("header")
        h.setFixedHeight(74)
        lay = QHBoxLayout(h)
        lay.setContentsMargins(18, 8, 22, 8)
        lay.setSpacing(14)
        logo = QLabel()
        logo.setPixmap(pixmap(asset("naygn_logo.png")).scaled(58, 58, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        lay.addWidget(logo)
        col = QVBoxLayout()
        col.setSpacing(0)
        t = QLabel("HALF-LIFE HACKER")
        t.setObjectName("appTitle")
        f = QFont(t.font())
        f.setLetterSpacing(QFont.AbsoluteSpacing, 3)
        t.setFont(f)
        s = QLabel("Fission product decay chains & their consequences  ·  NAYGN McMaster workshop")
        s.setObjectName("appSub")
        col.addWidget(t)
        col.addWidget(s)
        lay.addLayout(col)
        lay.addStretch(1)
        self.progress_text = QLabel("")
        self.progress_text.setObjectName("progressText")
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedWidth(220)
        pc = QVBoxLayout()
        pc.setSpacing(4)
        pc.addWidget(self.progress_text, 0, Qt.AlignRight)
        pc.addWidget(self.progress_bar)
        lay.addLayout(pc)
        return h

    def _build_sidebar(self) -> QTreeWidget:
        tree = QTreeWidget()
        tree.setObjectName("sidebar")
        tree.setHeaderHidden(True)
        tree.setFixedWidth(280)
        tree.setIndentation(10)
        tree.setTextElideMode(Qt.ElideRight)
        tree.setFocusPolicy(Qt.NoFocus)
        self.items: dict[str, QTreeWidgetItem] = {}
        for sec in SECTIONS:
            top = QTreeWidgetItem(tree, [SHORT.get(sec.id, sec.title).upper()])
            top.setFlags(Qt.ItemIsEnabled)
            f = top.font(0)
            f.setBold(True)
            f.setPointSizeF(8.8)
            f.setLetterSpacing(QFont.AbsoluteSpacing, 1)
            top.setFont(0, f)
            top.setForeground(0, Qt.white)
            top.setToolTip(0, f"{sec.rung}: {sec.title}" if sec.rung else sec.title)
            for st in sec.steps:
                it = QTreeWidgetItem(top, [""])
                it.setData(0, Qt.UserRole, st.id)
                self.items[st.id] = it
            top.setExpanded(True)
        tree.setExpandsOnDoubleClick(False)
        tree.itemClicked.connect(self._on_tree_click)
        self.tops = [tree.topLevelItem(i) for i in range(tree.topLevelItemCount())]
        return tree

    def _build_navbar(self) -> QWidget:
        n = QFrame()
        n.setObjectName("navbar")
        n.setFixedHeight(58)
        lay = QHBoxLayout(n)
        lay.setContentsMargins(18, 8, 18, 8)
        self.menu_btn = QPushButton("☰")
        self.menu_btn.setToolTip("Show / hide the step list (Ctrl+B)")
        self.menu_btn.setFixedWidth(44)
        self.menu_btn.clicked.connect(self.toggle_sidebar)
        self.back_btn = QPushButton("◀  Back")
        self.next_btn = QPushButton("Next  ▶")
        self.next_btn.setObjectName("primary")
        self.step_title = QLabel("")
        self.step_title.setStyleSheet("font-weight:600; font-size: 11pt;")
        self.step_counter = QLabel("")
        self.step_counter.setObjectName("stepCounter")
        self.back_btn.clicked.connect(self.back)
        self.next_btn.clicked.connect(self.next)
        lay.addWidget(self.menu_btn)
        lay.addWidget(self.back_btn)
        lay.addSpacing(12)
        lay.addWidget(self.step_title)
        lay.addStretch(1)
        lay.addWidget(self.step_counter)
        lay.addSpacing(14)
        lay.addWidget(self.next_btn)
        return n

    def _build_menus(self):
        mb = self.menuBar()
        fm = mb.addMenu("&File")
        self._act(fm, "Export my code…", self.export_code, "Ctrl+E")
        fm.addSeparator()
        self._act(fm, "Reset this step", self.reset_current)
        self._act(fm, "Reset ALL progress…", self.reset_all)
        fm.addSeparator()
        self._act(fm, "Quit", self.close, "Ctrl+Q")
        vm = mb.addMenu("&View")
        self._act(vm, "Bigger text (projector)", lambda: self.zoom(+1), "Ctrl+=")
        self._act(vm, "Smaller text", lambda: self.zoom(-1), "Ctrl+-")
        self._act(vm, "Reset text size", lambda: self.zoom(0), "Ctrl+0")
        vm.addSeparator()
        self._act(vm, "Show / hide sidebar", self.toggle_sidebar, "Ctrl+B")
        self._act(vm, "Full screen", self.toggle_fullscreen, "F11")
        rm = mb.addMenu("&Run")
        self._act(rm, "Run this step", self.run_current, "F5")
        hm = mb.addMenu("&Help")
        self._act(hm, "Keyboard shortcuts", self.show_shortcuts)
        self._act(hm, "About", self.about)

    def _act(self, menu, text, slot, shortcut=None):
        a = QAction(text, self)
        if shortcut:
            a.setShortcut(QKeySequence(shortcut))
        a.triggered.connect(lambda _=False: slot())
        menu.addAction(a)
        return a

    # ------------------------------------------------------------------ navigation
    def view_for(self, step_id: str) -> StepView:
        if step_id not in self.views:
            sec, si = self.sec_of[step_id]
            st = next(s for s in sec.steps if s.id == step_id)
            v = StepView(st, sec, si, self.ctx)
            if st.kind == "final":
                v.export_btn.clicked.connect(self.export_code)
            self.stack.addWidget(v)
            self.views[step_id] = v
        return self.views[step_id]

    def current_view(self) -> StepView:
        return self.views[ALL_STEPS[self.current].id]

    def go(self, i: int):
        i = max(0, min(len(ALL_STEPS) - 1, i))
        st = ALL_STEPS[i]
        self.current = i
        view = self.view_for(st.id)
        self.stack.setCurrentWidget(view)
        self.tree.setCurrentItem(self.items[st.id])
        cur_top = self.items[st.id].parent()
        for t in self.tops:                       # accordion: keep only the current section open
            t.setExpanded(t is cur_top)
        self.ctx.progress.last = st.id
        self.ctx.save_soon()
        if st.kind == "info":
            self.ctx.mark(st.id, True)
        self.back_btn.setEnabled(i > 0)
        self.next_btn.setEnabled(i < len(ALL_STEPS) - 1)
        self.step_title.setText(st.title)
        self.step_counter.setText(f"Step {i + 1} of {len(ALL_STEPS)}")
        self.refresh_progress()

    def next(self):
        self.go(self.current + 1)

    def back(self):
        self.go(self.current - 1)

    def _on_tree_click(self, item, _col):
        sid = item.data(0, Qt.UserRole)
        if sid:
            self.go(self.index_of[sid])
        else:
            item.setExpanded(not item.isExpanded())   # click a section title to fold / unfold it

    # ------------------------------------------------------------------ progress
    def refresh_progress(self):
        done = self.ctx.progress.done
        for st in ALL_STEPS:
            it = self.items[st.id]
            mark = "✓" if st.id in done else "○"
            lab = f"{st.label}  " if st.label else ""
            it.setText(0, f"{mark}   {lab}{st.title}")
            it.setForeground(0, Qt.white if st.id in done else Qt.lightGray)
        inter = [s for s in ALL_STEPS if s.kind in INTERACTIVE]
        n = sum(1 for s in inter if s.id in done)
        self.progress_bar.setRange(0, len(inter))
        self.progress_bar.setValue(n)
        self.progress_text.setText(f"{n} of {len(inter)} activities complete")
        # make "Next" glow once this step is finished
        cur = ALL_STEPS[self.current] if self.current >= 0 else None
        if cur is not None:
            ready = cur.id in done and self.current < len(ALL_STEPS) - 1
            self.next_btn.setObjectName("glow" if ready and cur.kind in INTERACTIVE else "primary")
            self.next_btn.style().unpolish(self.next_btn)
            self.next_btn.style().polish(self.next_btn)

    # ------------------------------------------------------------------ actions
    def run_current(self):
        v = self.current_view()
        if v.editor is not None:
            v.run()

    def reset_current(self):
        v = self.current_view()
        if v.editor is not None:
            v.reset_code()

    def reset_all(self):
        r = QMessageBox.warning(self, "Reset everything?",
                                "This clears ALL your code and progress and starts the workshop from the beginning.",
                                QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
        if r != QMessageBox.Yes:
            return
        self.ctx.progress.reset()
        self.ctx.session.reset()
        for v in list(self.views.values()):
            v.dispose()
            self.stack.removeWidget(v)
            v.deleteLater()
        self.views.clear()
        self.go(0)

    def zoom(self, d):
        if d == 0:
            self.ctx.text_zoom, self.ctx.editor_pt = 0, 11.5
        else:
            self.ctx.text_zoom = max(-3, min(10, self.ctx.text_zoom + d))
            self.ctx.editor_pt = max(8.5, min(26, self.ctx.editor_pt + d))
        for v in self.views.values():
            v.apply_zoom()

    def toggle_sidebar(self):
        self._sidebar_user_set = True
        self.tree.setVisible(not self.tree.isVisible())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if not self._sidebar_user_set and hasattr(self, "tree"):
            self.tree.setVisible(self.width() >= 1200)   # small laptop screens: more room for code + plot

    def toggle_fullscreen(self):
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def export_code(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export my code", "my_half_life_hacker.py", "Python file (*.py)")
        if not path:
            return
        self.write_export(path)
        self.statusBar().showMessage(f"Saved {path}", 5000)

    def write_export(self, path):
        parts = ["# Half-Life Hacker — my work (NAYGN McMaster workshop)\n"
                 "# Run top-to-bottom, like notebook cells. Needs: numpy, scipy, matplotlib.\n\n",
                 "# " + "=" * 70 + "\n# Setup\n# " + "=" * 70 + "\n", PRELUDE, "\n"]
        for st in ALL_STEPS:
            if not st.code:
                continue
            code = self.ctx.progress.code.get(st.id, st.code)
            parts.append("\n# " + "=" * 70 + f"\n# Step {st.label or '0'} — {st.title}\n# " + "=" * 70 + "\n")
            parts.append(code.rstrip() + "\n")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("".join(parts))

    def show_shortcuts(self):
        QMessageBox.information(self, "Keyboard shortcuts",
                                "Ctrl+Enter / F5     Run the current step\n"
                                "Alt+→ / Alt+←       Next / previous step\n"
                                "Ctrl+ =  /  Ctrl+ -   Bigger / smaller text (projector mode)\n"
                                "F11                 Full screen\n"
                                "Ctrl+B              Show / hide the sidebar (more room on small screens)\n"
                                "Tab / Shift+Tab     Indent / un-indent in the editor\n"
                                "Ctrl+E              Export my code")

    def about(self):
        QMessageBox.about(self, "About Half-Life Hacker",
                          f"<h3>Half-Life Hacker {VERSION}</h3>"
                          "<p>A hands-on computational nuclear physics workshop.<br>"
                          "Simulating fission product decay chains — and why xenon makes a reactor harder to restart.</p>"
                          "<p><b>NAYGN McMaster</b><br>North American Young Generation in Nuclear</p>"
                          "<p>Photography: McMaster Nuclear Reactor (MNR).</p>")

    def closeEvent(self, e):
        self.ctx.progress.save()
        super().closeEvent(e)
