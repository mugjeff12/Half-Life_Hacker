"""A small, friendly Python code editor: line numbers, syntax colours, TODO highlighting, auto-indent."""
from __future__ import annotations

import keyword
import re

from PySide6.QtCore import QRect, QRegularExpression, QSize, Qt, Signal
from PySide6.QtGui import (QColor, QFont, QFontDatabase, QFontMetricsF, QPainter, QSyntaxHighlighter,
                           QTextCharFormat, QTextCursor, QTextFormat)
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget

from . import theme
from .theme import SYN


def mono_font(pt: float = 11.5) -> QFont:
    fams = set(QFontDatabase.families())
    for name in theme.MONO_FONTS:
        if name in fams:
            f = QFont(name, int(pt))
            f.setPointSizeF(pt)
            return f
    f = QFontDatabase.systemFont(QFontDatabase.FixedFont)
    f.setPointSizeF(pt)
    return f


def _fmt(color, bold=False, italic=False, bg=None):
    f = QTextCharFormat()
    f.setForeground(QColor(color))
    if bold:
        f.setFontWeight(QFont.Bold)
    f.setFontItalic(italic)
    if bg:
        f.setBackground(QColor(bg))
    return f


class PythonHighlighter(QSyntaxHighlighter):
    BUILTINS = ("print len range abs min max sum float int str list dict tuple set zip enumerate isinstance "
                "np plt solve_ivp check self").split()

    def __init__(self, doc, todo_mode=False):
        super().__init__(doc)
        self.todo_mode = todo_mode
        self.f_kw = _fmt(SYN["keyword"], bold=True)
        self.f_builtin = _fmt(SYN["builtin"])
        self.f_num = _fmt(SYN["number"])
        self.f_str = _fmt(SYN["string"])
        self.f_com = _fmt(SYN["comment"], italic=True)
        self.f_todo = _fmt(SYN["todo"], bold=True, italic=True)
        self.f_def = _fmt(SYN["defname"], bold=True)
        self.f_none = _fmt("#FFFFFF", bold=True, bg="#7E0237")
        kws = [k for k in keyword.kwlist if k not in ("None", "True", "False")]
        self.rx_kw = QRegularExpression(r"\b(" + "|".join(kws) + r")\b")
        self.rx_builtin = QRegularExpression(r"\b(" + "|".join(self.BUILTINS) + r")\b")
        self.rx_const = QRegularExpression(r"\b(True|False)\b")
        self.rx_none = QRegularExpression(r"\bNone\b")
        self.rx_num = QRegularExpression(r"\b\d+\.?\d*([eE][+-]?\d+)?\b|\.\d+([eE][+-]?\d+)?")
        self.rx_def = QRegularExpression(r"\b(?:def|class)\s+(\w+)")
        self.rx_str = QRegularExpression(r'"[^"\\\n]*(\\.[^"\\\n]*)*"|\'[^\'\\\n]*(\\.[^\'\\\n]*)*\'')

    def _apply(self, rx, fmt, text, group=0):
        it = rx.globalMatch(text)
        while it.hasNext():
            m = it.next()
            self.setFormat(m.capturedStart(group), m.capturedLength(group), fmt)

    def highlightBlock(self, text):
        self._apply(self.rx_num, self.f_num, text)
        self._apply(self.rx_builtin, self.f_builtin, text)
        self._apply(self.rx_const, self.f_kw, text)
        self._apply(self.rx_kw, self.f_kw, text)
        self._apply(self.rx_def, self.f_def, text, 1)
        self._apply(self.rx_none, self.f_none if self.todo_mode else self.f_kw, text)
        self._apply(self.rx_str, self.f_str, text)
        # comment: first '#' that is not inside a string
        quote, esc = None, False
        for i, ch in enumerate(text):
            if quote:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == quote:
                    quote = None
            elif ch in "\"'":
                quote = ch
            elif ch == "#":
                is_todo = "TODO" in text[i:]
                self.setFormat(i, len(text) - i, self.f_todo if is_todo else self.f_com)
                break


class _Gutter(QWidget):
    def __init__(self, ed):
        super().__init__(ed)
        self.ed = ed

    def sizeHint(self):
        return QSize(self.ed.gutter_width(), 0)

    def paintEvent(self, e):
        self.ed.paint_gutter(e)


class CodeEditor(QPlainTextEdit):
    run_requested = Signal()

    def __init__(self, readonly=False, todo_mode=False, parent=None):
        super().__init__(parent)
        self.setFont(mono_font())
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setReadOnly(readonly)
        self.setTabStopDistance(QFontMetricsF(self.font()).horizontalAdvance(" ") * 4)
        self.highlighter = PythonHighlighter(self.document(), todo_mode)
        self.gutter = _Gutter(self)
        self.blockCountChanged.connect(self._update_margin)
        self.updateRequest.connect(self._update_gutter)
        self.cursorPositionChanged.connect(self._extra_selections)
        self.textChanged.connect(self._extra_selections)
        self._update_margin()
        self._extra_selections()

    # -- font zoom ------------------------------------------------------------
    def set_point_size(self, pt: float):
        f = self.font()
        f.setPointSizeF(pt)
        self.setFont(f)
        self.setTabStopDistance(QFontMetricsF(f).horizontalAdvance(" ") * 4)
        self._update_margin()

    # -- gutter ---------------------------------------------------------------
    def gutter_width(self):
        digits = max(2, len(str(max(1, self.blockCount()))))
        return 16 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_margin(self, *_):
        self.setViewportMargins(self.gutter_width(), 0, 0, 0)

    def _update_gutter(self, rect, dy):
        if dy:
            self.gutter.scroll(0, dy)
        else:
            self.gutter.update(0, rect.y(), self.gutter.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_margin()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        cr = self.contentsRect()
        self.gutter.setGeometry(QRect(cr.left(), cr.top(), self.gutter_width(), cr.height()))

    def paint_gutter(self, e):
        p = QPainter(self.gutter)
        p.fillRect(e.rect(), QColor("#101010"))
        block = self.firstVisibleBlock()
        n = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        cur = self.textCursor().blockNumber()
        h = self.fontMetrics().height()
        while block.isValid() and top <= e.rect().bottom():
            if block.isVisible() and bottom >= e.rect().top():
                is_todo = "TODO" in block.text() and "#" in block.text()
                p.setPen(QColor("#FF8FB3") if is_todo else QColor("#FFFFFF") if n == cur else QColor("#5E5E5E"))
                p.drawText(0, top, self.gutter.width() - 8, h, Qt.AlignRight, str(n + 1))
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            n += 1

    # -- highlights: current line + TODO lines --------------------------------
    def _extra_selections(self):
        sels = []
        doc = self.document()
        blk = doc.firstBlock()
        while blk.isValid():
            t = blk.text()
            if "TODO" in t and "#" in t:
                s = QTextEdit.ExtraSelection()
                s.format.setBackground(QColor(126, 2, 55, 85))
                s.format.setProperty(QTextFormat.FullWidthSelection, True)
                cur = self.textCursor()
                cur.setPosition(blk.position())
                s.cursor = cur
                sels.append(s)
            blk = blk.next()
        if not self.isReadOnly():
            s = QTextEdit.ExtraSelection()
            s.format.setBackground(QColor(255, 255, 255, 14))
            s.format.setProperty(QTextFormat.FullWidthSelection, True)
            s.cursor = self.textCursor()
            s.cursor.clearSelection()
            sels.append(s)
        self.setExtraSelections(sels)

    # -- typing niceties ------------------------------------------------------
    def keyPressEvent(self, e):
        k, mods = e.key(), e.modifiers()
        if k in (Qt.Key_Return, Qt.Key_Enter) and mods & Qt.ControlModifier:
            self.run_requested.emit()
            return
        if self.isReadOnly():
            return super().keyPressEvent(e)
        cur = self.textCursor()
        if k == Qt.Key_Tab and not (mods & Qt.ShiftModifier):
            if cur.hasSelection():
                self._indent_selection(+1)
            else:
                cur.insertText("    ")
            return
        if k == Qt.Key_Backtab or (k == Qt.Key_Tab and mods & Qt.ShiftModifier):
            self._indent_selection(-1)
            return
        if k in (Qt.Key_Return, Qt.Key_Enter):
            line = cur.block().text()[: cur.positionInBlock()]
            indent = re.match(r"\s*", line).group(0)
            if line.rstrip().endswith(":"):
                indent += "    "
            cur.insertText("\n" + indent)
            self.setTextCursor(cur)
            self.ensureCursorVisible()
            return
        super().keyPressEvent(e)

    def _indent_selection(self, direction):
        cur = self.textCursor()
        doc = self.document()
        start_b = doc.findBlock(cur.selectionStart())
        end_b = doc.findBlock(cur.selectionEnd())
        cur.beginEditBlock()
        b = start_b
        while True:
            c = self.textCursor()
            c.setPosition(b.position())
            if direction > 0:
                c.insertText("    ")
            else:
                txt = b.text()
                n = min(4, len(txt) - len(txt.lstrip(" ")))
                c.setPosition(b.position() + n, QTextCursor.KeepAnchor)
                c.removeSelectedText()
            if b == end_b:
                break
            b = b.next()
        cur.endEditBlock()
