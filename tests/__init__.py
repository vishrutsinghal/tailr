"""Test package bootstrap: make flat script imports resolvable.

The pipeline scripts (e.g. ``scripts/pipeline_manager.py``,
``scripts/pipeline_orchestrator.py``) import their siblings as top-level
modules (``import planning_lock``). Adding ``scripts/`` to ``sys.path`` here
makes every ``python3 -m unittest tests.<module>`` invocation work without
external configuration or ``PYTHONPATH``.
"""

import sys
from pathlib import Path

SCRIPTS_DIR = str(Path(__file__).resolve().parents[1] / "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)