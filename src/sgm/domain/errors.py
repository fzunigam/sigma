class DomainValidationError(ValueError):
    """Raised when a domain invariant is violated."""


class NoMarkedMovementsError(DomainValidationError):
    """Raised when rendering is requested without marked movements."""
