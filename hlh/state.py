"""App context: shared session + auto-saved progress (so a closed laptop never loses a student's work)."""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QObject, QStandardPaths, QTimer, Signal


class Progress:
    def __init__(self, path: Path | None):
        self.path = path
        self.code: dict = {}
        self.done: set = set()
        self.extras: dict = {}
        self.last: str = ""
        self._load()

    def _load(self):
        if not self.path or not self.path.exists():
            return
        try:
            d = json.loads(self.path.read_text(encoding="utf-8"))
            self.code = dict(d.get("code", {}))
            self.done = set(d.get("done", []))
            self.extras = dict(d.get("extras", {}))
            self.last = d.get("last", "")
        except Exception:
            pass   # a corrupt file just means "start fresh"

    def save(self):
        if not self.path:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(
                {"code": self.code, "done": sorted(self.done), "extras": self.extras, "last": self.last},
                ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception:
            pass

    def reset(self):
        self.code, self.done, self.extras, self.last = {}, set(), {}, ""
        self.save()


def default_progress_path() -> Path:
    base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    return Path(base) / "progress.json"


class AppContext(QObject):
    progress_changed = Signal()
    status = Signal(str)

    def __init__(self, session, progress: Progress):
        super().__init__()
        self.session = session
        self.progress = progress
        self.editor_pt = 11.5
        self.text_zoom = 0
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self.progress.save)

    def save_soon(self):
        self._save_timer.start(700)

    def mark(self, step_id: str, done: bool):
        changed = (step_id in self.progress.done) != done
        if done:
            self.progress.done.add(step_id)
        else:
            self.progress.done.discard(step_id)
        self.save_soon()
        if changed:
            self.progress_changed.emit()
