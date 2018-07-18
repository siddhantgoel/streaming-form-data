from unittest import TestCase

from streaming_form_data.validators import MaxSizeValidator, ValidationError


class MaxSizeValidatorTestCase(TestCase):
    def test_max_size(self):
        validator = MaxSizeValidator(5)

        for char in 'hello':
            validator(char)

        self.assertRaises(ValidationError, validator, 'x')
