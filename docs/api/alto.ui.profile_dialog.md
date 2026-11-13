---
title: alto.ui.profile_dialog
parent: api
package: alto.ui
order: 27
permalink: /api/alto.ui.profile_dialog/
---
{% raw %}
Choosing who is practising. There is no password: a profile is just a name that keeps its own history.

**Examples**

```pycon
>>> db = Database()
>>> remember_profile(db.add_profile("Ada"))
>>> # noinspection PyUnresolvedReferences
>>> startup_profile(db).name  # the one used last time, with no dialog
'Ada'
```

## ProfileDialog

```python
ProfileDialog(
    db: Database,
    *,
    current: Profile | None = None,
    parent: QWidget | None = None,
)
```

Bases: `QDialog`

Ask who is practising: a first name on launch, then a list to switch between.

On first launch (no profiles yet) it asks for a name. Afterwards it lists the profiles to switch between and lets you add
another.

**Attributes**

- `db` (*Database*): Where the profiles are kept.
- `chosen` (*Profile or None*): The profile that was picked or created, once the dialog is accepted.
- `list` (*QListWidget*): The existing profiles.
- `name` (*QLineEdit*): Where a new name is typed.
- `error` (*QLabel*): Says why a name was refused.

**Examples**

```pycon
>>> db = Database()
>>> dialog = ProfileDialog(db)
>>> dialog.windowTitle()  # nobody has a profile yet
'Welcome'
```

**Constructor**

Build the dialog for the profiles in a database.

**Parameters**

- `db` (*Database*): The database whose profiles are listed and added to.
- `current` (*Profile or None, default None*): The profile to select in the list at first. Keyword-only.
- `parent` (*QWidget or None, default None*): The widget that owns the dialog. Keyword-only.

**Constructor examples**

```pycon
>>> database = Database()
>>> _ = database.add_profile("Ada")
>>> ProfileDialog(database).windowTitle()
'Profile'
```

## remember_profile

```python
def remember_profile(profile: Profile) -> None
```

Remember which profile was used, so the next launch can open with it.

**Parameters**

- `profile` (*Profile*): The profile in use.

**Examples**

```pycon
>>> remember_profile(Profile(7, name="Ada"))
>>> int_value(store(), key="profile/last", default=-1)
7
```

## startup_profile

```python
def startup_profile(db: Database) -> Profile | None
```

Return the profile to open with: the one used last time, else ask.

**Parameters**

- `db` (*Database*): The database of profiles.

**Returns**

- *Profile or None*: The profile, or None if the person closed the dialog without choosing one.

**Examples**

```pycon
>>> database = Database()
>>> ada = database.add_profile("Ada")
>>> remember_profile(ada)
>>> # noinspection PyUnresolvedReferences
>>> startup_profile(database).name
'Ada'
```
{% endraw %}
