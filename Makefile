cython-file := streaming_form_data/_parser.pyx

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf streaming_form_data.egg-info

# development

annotate:
	cython -a $(cython-file) -o build/annotation.html

compile:
	cython $(cython-file)

pip-compile:
	pip-compile requirements-dev.in > requirements-dev.txt

# lint

fmt-black:
	black streaming_form_data/*.py tests/ utils/ examples/**/*.py

lint-black:
	black --check streaming_form_data/*.py tests/ utils/ examples/**/*.py

lint-flake8:
	flake8 streaming_form_data/*.py tests/ utils/ examples/**/*.py

lint-mypy:
	mypy streaming_form_data/

lint: lint-black lint-flake8 lint-mypy

# test

test-pytest:
	py.test tests/

test: test-pytest

# utils

profile:
	python utils/profile.py --data-size 17555000 -c binary/octet-stream

speed-test:
	python utils/speedtest.py

.PHONY: clean \
	annotate compile \
	pip-compile \
	lint-black lint-flake8 lint-mypy lint \
	test-pytest test \
	speed-test profile
