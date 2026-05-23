"""Chat router (sessions + message POST that invokes the agent graph).

Stub for Wave 1.
"""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/chat", tags=["chat"])
