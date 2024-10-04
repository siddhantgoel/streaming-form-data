parser_pyx := "src/streaming_form_data/_parser.pyx"

# development

annotate:
    uv run cython --annotate {{parser_pyx}} --output build/annotation.html

# lint

lint: lint-ruff lint-mypy

lint-ruff:
    uv run ruff check src/ tests/ examples/

lint-mypy:
    uv run mypy src/

# test

test: test-pytest

test-pytest:
    uv run pytest tests/

# utils

profile:
	uv run python utils/profile.py --data-size 17555000 -c binary/octet-stream

speed-test:
    uv run python utils/speed_test.py
