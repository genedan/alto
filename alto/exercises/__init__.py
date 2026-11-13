"""
The exercises and the framework they are built on.

Importing this package registers every exercise in `REGISTRY`, in the order the home screen shows them.

Examples
--------
>>> len(REGISTRY) >= 8
True
>>> Question("Name it.", choices=["C", "D"], answer="C").check("C")
True
"""

from alto.exercises import library  # noqa: F401  (registers exercises)
from alto.exercises.base import (
    REGISTRY,
    Exercise,
    Question,
)

__all__ = ["REGISTRY", "Exercise", "Question"]
