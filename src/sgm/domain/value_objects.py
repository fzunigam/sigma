from dataclasses import dataclass

from .errors import DomainValidationError


@dataclass(frozen=True)
class CLPAmount:
    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or self.value <= 0:
            raise DomainValidationError("CLP amount must be a positive integer")
