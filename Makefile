clean:
	rm -f dist/*.tar.gz
	rm -f dist/*.whl
	rm -rf build

build:
	python setup.py sdist

upload: build
	twine upload dist/*

test:
	PYTHONPATH=. py.test
	flake8

.PHONY: clean build upload
