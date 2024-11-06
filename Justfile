parser_pyx := "streaming_form_data/_parser.pyx"

# development

annotate:
    poetry run cython --annotate {{parser_pyx}} --output build/annotation.html

compile:
    poetry run cython {{parser_pyx}}

server:
    poetry run python utils/server.py

# lint

lint: lint-ruff lint-mypy

lint-ruff:
    poetry run ruff check streaming_form_data/ tests/ examples/

lint-mypy:
    poetry run mypy streaming_form_data/

# test

test: test-pytest

test-pytest:
    poetry run pytest tests/

# utils

profile:
	poetry run python utils/profile.py --data-size 17555000 -c binary/octet-stream

speed-test:
    poetry run python utils/speed_test.py
