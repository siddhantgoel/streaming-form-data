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
	pip-compile requirements.in > requirements.txt

pip-sync:
	pip-sync requirements.txt

# lint

fmt-black:
	black streaming_form_data/*.py tests/ utils/ examples/**/*.py

lint-black:
	black --check streaming_form_data/*.py tests/ utils/ examples/**/*.py

lint-ruff:
	ruff --select=B,C4,C9,E,F,PLC,PLE,PLW,W .

lint-mypy:
	mypy streaming_form_data/

lint: lint-ruff lint-black lint-mypy

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
	pip-compile pip-sync \
	lint-black lint-flake8 lint-mypy lint \
	test-pytest test \
	speed-test profile
