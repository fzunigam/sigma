import pytest

from sgm.domain.errors import DomainValidationError
from sgm.domain.value_objects import CLPAmount


def test_clp_amount_accepts_positive_int() -> None:
    assert CLPAmount(1500).value == 1500


@pytest.mark.parametrize("invalid_value", [-1, 1.5, "1000", None, True])
def test_clp_amount_rejects_invalid_values(invalid_value: object) -> None:
    with pytest.raises(DomainValidationError):
        CLPAmount(invalid_value)  # type: ignore[arg-type]
