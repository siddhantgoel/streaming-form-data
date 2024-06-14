from setuptools import Extension


def build(setup_kwargs):
    setup_kwargs.update(
        {
            "ext_modules": [
                Extension(
                    "streaming_form_data._parser",
                    ["streaming_form_data/_parser.c"],
                )
            ]
        }
    )
