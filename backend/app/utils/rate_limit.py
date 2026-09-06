"""
Rate limiting via slowapi (a Flask-Limiter-style wrapper for FastAPI/Starlette).
In-memory storage is fine for a single-instance deployment; if you ever run
multiple backend instances behind a load balancer, point this at Redis
instead (slowapi supports it via `storage_uri`) so limits are shared
across instances rather than reset per-instance.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
