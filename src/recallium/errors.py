"""Typed errors for Recallium Core."""


class RecalliumError(Exception):
    """Base class for Recallium domain errors."""


class ValidationError(RecalliumError):
    """Raised when inputs fail Recallium validation."""


class NotFoundError(RecalliumError):
    """Raised when a requested memory cannot be found."""


class EmbeddingProviderUnavailableError(RecalliumError):
    """Raised when the embedding provider runtime cannot be initialized."""


class EmbeddingModelUnavailableError(RecalliumError):
    """Raised when the configured embedding model cannot be loaded or cached."""


class EmbeddingGenerationError(RecalliumError):
    """Raised when embedding generation fails."""
