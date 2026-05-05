import pytest

from sgm.domain.accounts import Account, AccountType, transfer
from sgm.domain.errors import DomainValidationError


def test_transfer_updates_balances() -> None:
    source = Account(id="a1", name="Checking", kind=AccountType.DEBIT, balance=10_000)
    target = Account(id="a2", name="Wallet", kind=AccountType.DEBIT, balance=1_000)

    transfer(source, target, 2_500)

    assert source.balance == 7_500
    assert target.balance == 3_500


def test_transfer_rejects_insufficient_balance() -> None:
    source = Account(id="a1", name="Checking", kind=AccountType.DEBIT, balance=100)
    target = Account(id="a2", name="Wallet", kind=AccountType.DEBIT, balance=0)

    with pytest.raises(DomainValidationError):
        transfer(source, target, 200)
