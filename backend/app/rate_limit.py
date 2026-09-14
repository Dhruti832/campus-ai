"""Shared slowapi Limiter instance.

Kept in its own module (rather than defined in main.py) so route modules
can apply @limiter.limit(...) without importing the FastAPI app itself
and risking a circular import.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
