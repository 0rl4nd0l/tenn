from services.evaluation.evidence_utils import numeric_match


def test_numeric_match_rejects_substring() -> None:
    assert numeric_match(123, "Value is 12345") is False


def test_numeric_match_accepts_commas_and_spaces() -> None:
    assert numeric_match(1234, "Revenue 1,234") is True
    assert numeric_match(1234, "Revenue 1 234") is True


def test_numeric_match_requires_non_digit_boundaries() -> None:
    assert numeric_match(1234, "x1234y") is True
    assert numeric_match(1234, "12345") is False

