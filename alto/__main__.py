import sys
from pathlib import Path

from PySide6.QtCore import QStandardPaths
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .learning import Database, Learner
from .ui.main_window import MainWindow
from .ui.profile_dialog import startup_profile
from .ui.theme import apply_theme, saved_theme


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Alto")
    app.setApplicationDisplayName("Alto - Music Theory")
    apply_theme(saved_theme())
    app.setDesktopFileName("alto")  # lets the desktop match the window to alto.desktop and its icon
    app.setWindowIcon(QIcon(str(Path(__file__).parent / "assets" / "icon.svg")))
    db = Database(Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)) / "alto.db")
    profile = startup_profile(db)  # asks for a name the first time
    if profile is None:
        return 0
    app.learner = Learner(db, profile)  # kept on the app so a theme change can swap in a fresh window
    app.main_window = MainWindow(app.learner)  # kept on the app so a theme change can swap in a fresh window
    app.main_window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
