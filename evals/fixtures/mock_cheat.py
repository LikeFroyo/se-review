"""Test suite containing vacuous test adequacy cheat and tautological assertions."""
from unittest.mock import MagicMock

class OrderProcessor:
    def calculate_tax(self, amount: float, state: str) -> float:
        if state == "CA":
            return round(amount * 0.0725, 2)
        elif state == "NY":
            return round(amount * 0.08, 2)
        return 0.0

def test_calculate_tax_dishonest():
    """TEST ADEQUACY DEFECT:
    Mocks out the actual function under test and asserts True == True.
    Gives 100% false coverage metric on CI without verifying tax rates, rounding, or branch logic.
    """
    mock_calc = MagicMock(return_value=10.0)
    result = mock_calc(100.0, "CA")
    
    # Vacuous assertions: does not test OrderProcessor at all!
    assert mock_calc.called is True
    assert True is True
