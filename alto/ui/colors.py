"""Mixing colours. The interface blends palette colours to get its soft tints and highlights."""
from __future__ import annotations

from PySide6.QtGui import QColor


def blend(a: QColor, b: QColor, t: float) -> QColor:
    """The colour t of the way from a to b (0 is a, 1 is b)."""
    return QColor.fromRgbF(a.redF() + (b.redF() - a.redF()) * t,
                           a.greenF() + (b.greenF() - a.greenF()) * t,
                           a.blueF() + (b.blueF() - a.blueF()) * t)


def blend_name(a: QColor, b: QColor, t: float) -> str:
    """Hex name of `blend(a, b, t)`, for use in a stylesheet."""
    return blend(a, b, t).name()
