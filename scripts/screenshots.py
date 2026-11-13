#!/usr/bin/env python
"""Regenerate the screenshots in docs/assets/img, in the light and the dark theme.

    .venv/bin/python scripts/screenshots.py              # every picture, both themes
    .venv/bin/python scripts/screenshots.py --only home stats
    .venv/bin/python scripts/screenshots.py --theme dark --out /tmp/shots

Each picture is written as name.png (light) and name-dark.png. The docs page picks the right one with the theme
toggle, so both must exist. The script runs against a throwaway profile with made-up answers, and a temporary
settings and data folder, so it never reads or changes your own profile, history or settings.

It needs a display or Qt's offscreen platform (QT_QPA_PLATFORM=offscreen). Fonts are rendered a little differently
on each machine, so regenerate on the machine you normally use and check the pictures before committing them.

Never add a picture of the exercise-level settings (the pane behind the sliders button) here. See CLAUDE.md.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "assets" / "img"
THEMES = ("light", "dark")
# The pictures this script makes. A docs page includes each of them with shot.html.
SHOTS = (
    "home",
    "note-identification",
    "keyboard",
    "note-construction",
    "intervals",
    "arpeggios",
    "key-signatures",
    "stats",
    "stats-heatmap",
    "database",
    "question-preview",
    "settings",
    "settings-sound",
)


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--theme", choices=THEMES, help="only this theme (default: both)")
    ap.add_argument(
        "--only",
        nargs="+",
        choices=SHOTS,
        metavar="NAME",
        help=f"only these pictures: {', '.join(SHOTS)}",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=OUT,
        help="folder to write to (default: docs/assets/img)",
    )
    args = ap.parse_args()
    names = tuple(args.only or SHOTS)
    args.out.mkdir(parents=True, exist_ok=True)
    if args.theme:
        capture(args.theme, names=names, out=args.out)
        return 0
    # One process for each theme, each with its own throwaway settings and data folder.
    for theme in THEMES:
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, XDG_CONFIG_HOME=f"{tmp}/config", XDG_DATA_HOME=f"{tmp}/data")
            env.setdefault("QT_QPA_PLATFORM", "xcb" if os.environ.get("DISPLAY") else "offscreen")
            cmd = [
                sys.executable,
                str(Path(__file__).resolve()),
                "--theme",
                theme,
                "--out",
                str(args.out),
                "--only",
                *names,
            ]
            if subprocess.run(cmd, env=env, cwd=ROOT).returncode:
                return 1
    print(f"wrote {len(names) * len(THEMES)} pictures to {args.out}")
    return 0


def capture(
    theme: str,
    *,
    names: tuple[str, ...],
    out: Path,
) -> None:
    import json
    import random
    import time

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    sys.path.insert(0, str(ROOT))
    from alto.exercises import REGISTRY
    from alto.exercises.base import Question
    from alto.learning import Database, Learner
    from alto.ui.app_settings import AppSettingsDialog
    from alto.ui.database_page import ROW_ROLE, DatabasePage
    from alto.ui.main_window import MainWindow
    from alto.ui.question_preview import QuestionPreview
    from alto.ui.theme import apply_theme

    suffix = "" if theme == "light" else "-dark"
    app = QApplication([])
    apply_theme(theme)

    import alto.ui.exercise_view as ev  # the same questions in both themes, so the light and dark pictures match

    original = ev.ExerciseView.__init__
    ev.ExerciseView.__init__ = lambda self, exercise, *, rng=None, parent=None, learner=None: original(
        self,
        exercise,
        rng=random.Random(5),
        parent=parent,
        learner=learner,
    )

    def wait(ms: int = 450) -> None:
        end = time.time() + ms / 1000
        while time.time() < end:
            app.processEvents()

    def save(
        widget,
        *,
        name: str,
        width: int = 1400,
    ) -> None:
        if name not in names:
            return
        wait(250)
        pixmap = widget.grab()
        if pixmap.width() > width:
            pixmap = pixmap.scaledToWidth(width, Qt.TransformationMode.SmoothTransformation)
        pixmap.save(str(out / f"{name}{suffix}.png"), "PNG")

    # A made-up profile: five weeks of answers that slowly get better, after about a year of lighter practice.
    db = Database()
    learner = Learner(db, profile=db.add_profile("Ada"))
    rng = random.Random(11)
    now = time.time()
    for day in range(34, -1, -1):
        if rng.random() < 0.3:
            continue
        for _ in range(rng.randint(8, 28)):
            ex = rng.choice(REGISTRY)()
            q = ex.generate(rng)
            t, attempt = now - day * 86400 - rng.randint(0, 20000), 1
            accuracy = min(0.95, 0.55 + (34 - day) * 0.011)
            seconds = max(0.7, rng.gauss(ex.par_seconds * (1.7 - (34 - day) * 0.018), 1))
            while True:
                ok = rng.random() < accuracy if attempt == 1 else True
                learner.record(
                    ex,
                    question=q,
                    answer=q.answer if ok else "?",
                    correct=ok,
                    attempt_no=attempt,
                    seconds=seconds,
                    now=t + attempt * 5,
                )
                if ok:
                    break
                attempt += 1
                seconds = rng.uniform(1, 4)
    # The year before that, from its own generator so the recent weeks above come out the same as ever: mostly short
    # sessions on a few days a week, with a lull in the summer, which is what a real heatmap looks like.
    old = random.Random(12)
    for day in range(364, 34, -1):
        month = time.localtime(now - day * 86400).tm_mon
        chance = 0.22 if month in (6, 7) else 0.55
        if old.random() > chance:
            continue
        for _ in range(
            old.choice(
                (
                    3,
                    6,
                    10,
                    14,
                    20,
                    28,
                    38,
                ),
            ),
        ):
            ex = old.choice(REGISTRY)()
            q = ex.generate(old)
            t = now - day * 86400 - old.randint(0, 20000)
            ok = old.random() < 0.5 + 0.3 * (364 - day) / 330
            learner.record(
                ex,
                question=q,
                answer=q.answer if ok else "?",
                correct=ok,
                attempt_no=1,
                seconds=max(0.7, old.gauss(ex.par_seconds * 1.5, 1)),
                now=t,
            )

    window = MainWindow(learner)
    window.resize(1100, 720)
    window.show()
    wait()
    save(window, name="home")
    by_class = {c.__name__: c for c in REGISTRY}
    for cls, name in (
        ("NoteNames", "note-identification"),
        ("KeyboardNotes", "keyboard"),
        ("NoteConstruction", "note-construction"),
        ("IntervalNames", "intervals"),
        ("ArpeggioNames", "arpeggios"),
        ("KeySignatures", "key-signatures"),
    ):
        if cls == "KeySignatures":  # show a signature to read, on an alto clef staff, whatever the default is
            from alto import settings

            settings.key_signatures.questions = {"read"}
            settings.key_signatures.clefs = {"alto"}
            settings.key_signatures.modes = {"Major (Ionian)"}
            settings.key_signatures.keys = {-3}  # three flats, so there is something to read
        window.open_exercise(by_class[cls])
        wait(500)
        save(window, name=name)
    window.show_home()
    wait()
    window.open_stats()
    wait(400)
    save(window, name="stats", width=1500)
    if "stats-heatmap" in names:  # scroll down to the calendar of reviews and show it with the table under it
        from alto.ui.stats_dialog import StatsPage
        from PySide6.QtWidgets import QScrollArea

        stats_page = window._overlay
        assert isinstance(stats_page, StatsPage)
        scroller = stats_page.findChild(QScrollArea)
        assert scroller is not None
        scroller.verticalScrollBar().setValue(stats_page.heatmap.y() - 16)
        wait(300)
        save(window, name="stats-heatmap", width=1500)
    window.open_database()
    wait(400)
    save(window, name="database")
    page = window._overlay
    assert isinstance(page, DatabasePage)
    page.tabs["answers"].click()
    wait(200)
    row = next(page.proxy.index(r, 0) for r in range(page.proxy.rowCount()) if "Chord" in page.proxy.index(r, 1).data())
    answer = row.data(ROW_ROLE)
    preview = QuestionPreview(
        page._names[answer["exercise"]],
        question=Question.from_dict(json.loads(answer["payload"])),
        details=answer["details"],
        parent=window,
    )
    preview.show()
    wait(300)
    save(preview, name="question-preview", width=900)
    preview.close()
    window.show_home()

    # The app-wide settings: the Notation style section, and the Sound page showing the viola.
    dialog = AppSettingsDialog(window)
    dialog.resize(1000, 640)
    dialog.show()
    dialog.segment_buttons[1].click()
    wait(300)
    save(dialog, name="settings")
    dialog.categories.setCurrentRow(1)
    dialog.instruments.select("viola_bowed")
    wait(200)
    save(dialog, name="settings-sound", width=1000)
    dialog.close()


if __name__ == "__main__":
    raise SystemExit(main())
