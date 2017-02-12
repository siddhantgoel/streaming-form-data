clean:
	rm -f dist/*.tar.gz
	rm -f dist/*.whl

build:
	python setup.py bdist_wheel

upload: build
	twine upload dist/*

.PHONY: clean build upload
