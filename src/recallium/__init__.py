"""Recallium Core package."""

from recallium.config import RecalliumConfig
from recallium.core import RecalliumCore
from recallium.errors import (
    MigrationError,
    NotFoundError,
    RecalliumError,
    ServiceConflictError,
    ServiceError,
    ValidationError,
)
from recallium.models import (
    SPACE_USER,
    SPACE_WORKSPACE,
    STATUS_ACTIVE,
    STATUS_ARCHIVED,
    Memory,
    SearchResult,
)

__all__ = [
    "__version__",
    "Memory",
    "RecalliumConfig",
    "RecalliumCore",
    "RecalliumError",
    "SearchResult",
    "ValidationError",
    "NotFoundError",
    "MigrationError",
    "ServiceError",
    "ServiceConflictError",
    "SPACE_USER",
    "SPACE_WORKSPACE",
    "STATUS_ACTIVE",
    "STATUS_ARCHIVED",
]

__version__ = "0.1.0"
