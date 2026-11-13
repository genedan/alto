"""
Mixing colours. The interface blends palette colours to get its soft tints and highlights.

Examples
--------
>>> blend_name(QColor("#000000"), b=QColor("#ffffff"), t=0.5)
'#808080'
"""

from __future__ import annotations

from PySide6.QtGui import QColor


def blend(
    a: QColor,
    *,
    b: QColor,
    t: float,
) -> QColor:
    """
    Return the colour a given fraction of the way from one colour to another.

    Parameters
    ----------
    a : QColor
        The colour at 0.
    b : QColor
        The colour at 1. Keyword-only.
    t : float
        How far from `a` to `b`: 0 is `a`, 1 is `b`, 0.5 is halfway. Keyword-only.

    Returns
    -------
    QColor
        The blended colour.

    Examples
    --------
    >>> blend(QColor("#000000"), b=QColor("#ffffff"), t=0.0).name()
    '#000000'
    >>> blend(QColor("#ff0000"), b=QColor("#0000ff"), t=1.0).name()
    '#0000ff'
    """
    return QColor.fromRgbF(
        a.redF() + (b.redF() - a.redF()) * t,
        a.greenF() + (b.greenF() - a.greenF()) * t,
        a.blueF() + (b.blueF() - a.blueF()) * t,
    )


def blend_name(
    a: QColor,
    *,
    b: QColor,
    t: float,
) -> str:
    """
    Return the hex name of a blended colour, for use in a stylesheet.

    Parameters
    ----------
    a : QColor
        The colour at 0.
    b : QColor
        The colour at 1. Keyword-only.
    t : float
        How far from `a` to `b`. Keyword-only.

    Returns
    -------
    str
        The colour as '#rrggbb'.

    Examples
    --------
    >>> blend_name(QColor("#000000"), b=QColor("#ffffff"), t=1.0)
    '#ffffff'
    """
    return blend(a, b=b, t=t).name()
