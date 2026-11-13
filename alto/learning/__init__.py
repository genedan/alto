"""
Spaced repetition: who is learning (profiles), what they answered (a database) and what to ask next.

Examples
--------
>>> db = Database()
>>> learner = Learner(db, profile=db.add_profile("Ada"))
>>> learner.profile.name
'Ada'
"""

from .database import Database, Profile
from .learner import Learner

__all__ = ["Database", "Learner", "Profile"]
