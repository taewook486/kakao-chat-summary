"""UI Coordinators - Worker and operation coordination layer.

Coordinators manage complex multi-step operations and background workers,
separating worker lifecycle management from UI logic.

Modules:
    worker_coordinator: Background worker management (upload, sync, summary, recovery)
"""

from .worker_coordinator import WorkerCoordinator

__all__ = ["WorkerCoordinator"]
