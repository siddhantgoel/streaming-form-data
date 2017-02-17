clean:
	rm -f dist/*.tar.gz
	rm -f dist/*.whl
	rm -rf build

deps-compile:
	pip-compile --output-file requirements.dev.txt requirements.dev.in

build:
	python setup.py bdist_wheel

upload: build
	twine upload dist/*

test: clean
	python setup.py build install
	py.test tests/

style:
	flake8

.PHONY: clean build upload deps-compile
