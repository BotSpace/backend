"""Shared helpers for credentials views — mirrors cms.views._common."""
from __future__ import annotations

from rest_framework.exceptions import NotFound

from core.apps.cms.views._common import get_project_or_404  # reuse identical logic

__all__ = ["get_project_or_404"]
