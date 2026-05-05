from dataclasses import dataclass
from enum import Enum

from .errors import DomainValidationError


class MovementType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"


@dataclass
class Movement:
    description: str
    amount: int
    type: MovementType
    account_id: str
    marked: bool

    def __post_init__(self) -> None:
        if type(self.amount) is not int or self.amount <= 0:
            raise DomainValidationError("Movement amount must be a positive integer")

    @classmethod
    def new(
        cls,
        description: str,
        amount: int,
        type: MovementType,
        account_id: str,
    ) -> "Movement":
        return cls(
            description=description,
            amount=amount,
            type=type,
            account_id=account_id,
            marked=True,
        )
