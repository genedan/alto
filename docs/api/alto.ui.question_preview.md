---
title: alto.ui.question_preview
parent: api
package: alto.ui
order: 28
permalink: /api/alto.ui.question_preview/
---
{% raw %}
A popup showing a stored question the way the exercise showed it, with its answer.

**Examples**

```pycon
>>> question = Question("Name the note.", choices=["C", "D"], answer="C")
>>> QuestionPreview("Note Identification", question=question).windowTitle()
'Note Identification'
```

## QuestionPreview

```python
QuestionPreview(
    exercise_name: str,
    *,
    question: Question,
    details: list[str] | None = None,
    parent: QWidget | None = None,
)
```

Bases: `QDialog`

A question as it appeared (the notes on the staff, or the highlighted key), then what the answer is.

**Attributes**

- `question` (*Question*): The question being shown.

**Examples**

```pycon
>>> from alto.theory.pitch import Note
>>> question = Question("Name the note.", choices=["C", "D"], answer="C", staff=[[Note.parse("C4")]])
>>> dialog = QuestionPreview("Note Identification", question=question, details=["You answered: D"])
>>> dialog.question.answer
'C'
```

**Constructor**

Build the popup.

**Parameters**

- `exercise_name` (*str*): The exercise's name, shown as the title.
- `question` (*Question*): The question to show. Keyword-only.
- `details` (*list of str or None, default None*): Extra lines of HTML, such as what was answered and how long it took. Keyword-only.
- `parent` (*QWidget or None, default None*): The widget that owns the dialog. Keyword-only.

**Constructor examples**

```pycon
>>> from alto.theory.pitch import Note
>>> question_ = Question("", choices=["C"], answer="C", keyboard=Note.parse("C4"))
>>> QuestionPreview("Keyboard Identification", question=question_).minimumWidth()
560
```
{% endraw %}
