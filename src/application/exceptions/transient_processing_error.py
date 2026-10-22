class TransientProcessingError(RuntimeError):
    """Raised when a transient error occurs during processing, indicating that the operation can be retried."""
    pass