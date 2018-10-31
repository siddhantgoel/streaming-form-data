help:
	$(info The following make commands are available:)
	$(info clean             - remove all generated files and directories)
	$(info test-all          - install locally, prepare for PyPI, run tests, speed test, profiler)
	$(info build             - prepare PyPI module archive)
	$(info upload            - upload built module archive to PyPI)
	$(info install-local     - build the module in the current directory)
	$(info                     it will be available for import from the project root directory)
	$(info test              - run tests and check code formatting)
	$(info profile           - gather library function call statistics (time, count, ...))
	$(info speedtest         - calculate library bandwidth)
	@:

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf streaming_form_data.egg-info

cython-file          := streaming_form_data/_parser.pyx
install-local-output := build/install.touch
requirements-output  := build/requirements.touch

test-all: build test speedtest profile annotate ;

build: $(requirements-output)
	python setup.py sdist
	@echo "Build PyPI archive is complete."

upload: build
	twine upload dist/*

install-local: $(install-local-output) ;

test: $(install-local-output)
	py.test
	flake8

speedtest: $(install-local-output)
	python utils/speedtest.py

profile: $(install-local-output)
	python utils/profile.py --data-size 17555000 -c binary/octet-stream

annotate: $(requirements-output)
	mkdir -p build
	cython -a $(cython-file) -o build/annotation.html

# All targets where the names do not match any real file name

.PHONY: help clean test-all build upload install-local test speedtest profile annotate

# Real file rules

library_inputs := setup.py \
                  $(shell find streaming_form_data -maxdepth 1 -name "*.py") \
                  $(cython-file)

$(requirements-output):
	pipenv install --dev
	@mkdir -p "$(@D)" && touch "$@"

$(install-local-output): $(requirements-output) $(library_inputs)
	pipenv install
	@mkdir -p "$(@D)" && touch "$@"
