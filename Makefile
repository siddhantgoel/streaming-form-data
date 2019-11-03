POETRY=poetry run

cython-file := streaming_form_data/_parser.pyx

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf streaming_form_data.egg-info

# development

annotate:
	$(POETRY) cython -a $(cython-file) -o build/annotation.html

compile:
	$(POETRY) cython $(cython-file)

# lint

fmt-black:
	$(POETRY) black streaming_form_data/*.py tests/ utils/ examples/**/*.py build.py

lint-black:
	$(POETRY) black --check streaming_form_data/*.py tests/ utils/ examples/**/*.py build.py

lint-flake8:
	$(POETRY) flake8 streaming_form_data/*.py tests/ utils/ examples/**/*.py build.py

lint-mypy:
	$(POETRY) mypy streaming_form_data/

lint: lint-black lint-flake8 lint-mypy

# test

test-pytest:
	$(POETRY) py.test tests/

test: test-pytest

# utils

profile:
	$(POETRY) python utils/profile.py --data-size 17555000 -c binary/octet-stream

speed-test:
	$(POETRY) python utils/speedtest.py

.PHONY: clean \
	annotate compile \
	lint-black lint-flake8 lint-mypy lint \
	test-pytest test \
	speed-test profile
