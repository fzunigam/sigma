from dataclasses import dataclass
from enum import Enum

from .errors import DomainValidationError


class AccountType(str, Enum):
    DEBIT = "debit"
    CREDIT = "credit"


@dataclass
class Account:
    id: str
    name: str
    kind: AccountType
    balance: int


def transfer(source: Account, target: Account, amount: int) -> None:
    if amount <= 0:
        raise DomainValidationError("Transfer amount must be positive")
    if source.balance < amount:
        raise DomainValidationError("Insufficient balance")

    source.balance -= amount
    target.balance += amount
