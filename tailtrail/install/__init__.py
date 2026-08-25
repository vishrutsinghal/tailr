"""Transactional installation lifecycle for TailTrail host surfaces."""

from .engine import InstallEngine, InstallFailure, UncleanInterruption
from .models import InstallPlan, InstallResult

__all__ = ["InstallEngine", "InstallFailure", "InstallPlan", "InstallResult", "UncleanInterruption"]
