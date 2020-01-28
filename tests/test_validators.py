import pytest

from streaming_form_data.validators import MaxSizeValidator, ValidationError


def test_max_size():
    validator = MaxSizeValidator(5)

    for char in 'hello':
        validator(char)

    with pytest.raises(ValidationError):
        validator('x')
