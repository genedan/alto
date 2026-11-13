"""
Spaced repetition: who is learning (profiles), what they answered (a database) and what to ask next.

Examples
--------
>>> db = Database()
>>> learner_ = Learner(db, profile=db.add_profile("Ada"))
>>> learner_.profile.name
'Ada'
"""

from alto.learning.database import (
    Database,
    Profile,
)
from alto.learning.learner import Learner

__all__ = ["Database", "Learner", "Profile"]
