"""
Choosing who is practising. There is no password: a profile is just a name that keeps its own history.

Examples
--------
>>> db = Database()
>>> remember_profile(db.add_profile("Ada"))
>>> startup_profile(db).name  # the one used last time, with no dialog
'Ada'
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..learning import Database, Profile
from .store import int_value, store


class ProfileDialog(QDialog):
    """
    Ask who is practising: a first name on launch, then a list to switch between.

    On first launch (no profiles yet) it asks for a name. Afterwards it lists the profiles to switch between and lets you add
    another.

    Attributes
    ----------
    db : Database
        Where the profiles are kept.
    chosen : Profile or None
        The profile that was picked or created, once the dialog is accepted.
    list : QListWidget
        The existing profiles.
    name : QLineEdit
        Where a new name is typed.
    error : QLabel
        Says why a name was refused.

    Examples
    --------
    >>> db = Database()
    >>> dialog = ProfileDialog(db)
    >>> dialog.windowTitle()  # nobody has a profile yet
    'Welcome'
    """

    def __init__(
        self,
        db: Database,
        *,
        current: Profile | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """
        Build the dialog for the profiles in a database.

        Parameters
        ----------
        db : Database
            The database whose profiles are listed and added to.
        current : Profile or None, default None
            The profile to select in the list at first. Keyword-only.
        parent : QWidget or None, default None
            The widget that owns the dialog. Keyword-only.

        Examples
        --------
        >>> db = Database()
        >>> _ = db.add_profile("Ada")
        >>> ProfileDialog(db).windowTitle()
        'Profile'
        """
        super().__init__(parent)
        self.db = db
        self.chosen: Profile | None = None
        first_run = not db.profiles()
        self.setWindowTitle("Welcome" if first_run else "Profile")
        self.setModal(True)
        self.setMinimumWidth(380)
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        if first_run:
            lay.addWidget(QLabel("<h2>Welcome to Alto</h2>"))
            about = QLabel(
                "Create a profile so your progress is remembered. Questions you find hard come back more "
                "often, and ones you answer quickly and correctly fade away. There is no password.",
            )
        else:
            lay.addWidget(QLabel("<h3>Who is practising?</h3>"))
            about = QLabel("Each profile keeps its own history.")
        about.setWordWrap(True)
        about.setStyleSheet("color: gray;")
        lay.addWidget(about)

        self.list = QListWidget()
        self.list.setObjectName("categories")  # the rounded list style used in the settings dialog
        self.list.setVisible(not first_run)
        if not first_run:
            for p in db.profiles():
                item = QListWidgetItem(p.name)
                item.setData(Qt.ItemDataRole.UserRole, p)
                self.list.addItem(item)
                if current and p.id == current.id:
                    self.list.setCurrentItem(item)
            if self.list.currentItem() is None:
                self.list.setCurrentRow(0)
            self.list.itemDoubleClicked.connect(lambda _: self._use_selected())
            lay.addWidget(self.list)
            lay.addWidget(QLabel("<b>New profile</b>"))

        row = QHBoxLayout()
        self.name = QLineEdit()
        self.name.setPlaceholderText("Your name")
        self.name.setMaxLength(40)
        self.name.returnPressed.connect(self._create)
        self.create_button = QPushButton("Create profile" if first_run else "Add")
        self.create_button.clicked.connect(self._create)
        row.addWidget(self.name, 1)
        row.addWidget(self.create_button)
        lay.addLayout(row)
        self.error = QLabel()
        self.error.setStyleSheet("color: #c62828;")
        self.error.setWordWrap(True)
        lay.addWidget(self.error)

        buttons = QDialogButtonBox()
        if not first_run:
            use = buttons.addButton("Use selected profile", QDialogButtonBox.ButtonRole.AcceptRole)
            use.clicked.connect(self._use_selected)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel if not first_run else QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)
        self.name.setFocus()

    def _create(self) -> None:
        """
        Create the profile named in the box and close, or say why it cannot be made.

        Examples
        --------
        >>> db = Database()
        >>> dialog = ProfileDialog(db)
        >>> dialog._create()  # no name typed
        >>> dialog.error.text()
        'Enter a name for the profile.'
        >>> dialog.name.setText("Ada")
        >>> dialog._create()
        >>> dialog.chosen.name
        'Ada'
        """
        try:
            self.chosen = self.db.add_profile(self.name.text())
        except ValueError as e:
            self.error.setText(str(e))
            return
        self.accept()

    def _use_selected(self) -> None:
        """
        Choose the profile selected in the list and close.

        Examples
        --------
        >>> db = Database()
        >>> _ = db.add_profile("Ada")
        >>> dialog = ProfileDialog(db)
        >>> dialog._use_selected()
        >>> dialog.chosen.name
        'Ada'
        """
        item = self.list.currentItem()
        if item is not None:
            self.chosen = item.data(Qt.ItemDataRole.UserRole)
            self.accept()


def remember_profile(profile: Profile) -> None:
    """
    Remember which profile was used, so the next launch can open with it.

    Parameters
    ----------
    profile : Profile
        The profile in use.

    Examples
    --------
    >>> remember_profile(Profile(7, name="Ada"))
    >>> int_value(store(), key="profile/last", default=-1)
    7
    """
    store().setValue("profile/last", profile.id)


def startup_profile(db: Database) -> Profile | None:
    """
    Return the profile to open with: the one used last time, else ask.

    Parameters
    ----------
    db : Database
        The database of profiles.

    Returns
    -------
    Profile or None
        The profile, or None if the person closed the dialog without choosing one.

    Examples
    --------
    >>> db = Database()
    >>> ada = db.add_profile("Ada")
    >>> remember_profile(ada)
    >>> startup_profile(db).name
    'Ada'
    """
    profiles = db.profiles()
    if profiles:
        last = db.profile(int_value(store(), key="profile/last", default=-1))
        if last:
            return last
        if len(profiles) == 1:
            return profiles[0]
    dialog = ProfileDialog(db)
    if dialog.exec() != QDialog.DialogCode.Accepted or dialog.chosen is None:
        return None
    remember_profile(dialog.chosen)
    return dialog.chosen
