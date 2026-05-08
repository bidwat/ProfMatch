"""Compatibility wrapper for the canonical match API module.

The routed implementation lives in `apps.backend.app.api.match`.
This module remains import-safe for older references.
"""

from .match import router

__all__ = ["router"]
