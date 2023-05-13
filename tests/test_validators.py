import pytest

from streaming_form_data.validators import MaxSizeValidator, ValidationError


def test_max_size_validator_empty_input():
    validator = MaxSizeValidator(0)

    with pytest.raises(ValidationError):
        validator("x")


def test_max_size_validator_normal():
    validator = MaxSizeValidator(5)

    for char in "hello":
        validator(char)

    with pytest.raises(ValidationError):
        validator("x")
