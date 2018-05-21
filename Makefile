help:
	$(info The following make commands are available:)
	$(info clean             - remove all generated files and directories)
	$(info test-all          - install locally, prepare for PyPI, run tests, speed test, profiler)
	$(info build             - prepare PyPI module archive)
	$(info upload            - upload built module archive to PyPI)
	$(info install_local     - build the module in the current directory)
	$(info                     it will be available for import from the project root directory)
	$(info test              - run tests and check code formatting)
	$(info profile           - gather library function call statistics (time, count, ...))
	$(info speedtest         - calculate library bandwidth)
	@:

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf streaming_form_data.egg-info

cython_file          := streaming_form_data/_parser.pyx
install_local_output := build/install.touch
requirements_output  := build/requirements.touch

test-all: build test speedtest profile annotate ;

build: $(requirements_output)
	python setup.py sdist
	@echo "Build PyPI archive is complete."

upload: build
	twine upload dist/*

install_local: $(install_local_output) ;

test: $(install_local_output)
	py.test
	flake8

speedtest: $(install_local_output)
	python utils/speedtest.py

profile: $(install_local_output)
	python utils/profile.py --data-size 17555000 -c binary/octet-stream

annotate: $(requirements_output)
	mkdir -p build
	cython -a $(cython_file) -o build/annotation.html

# All targets where the names do not match any real file name

.PHONY: help clean test-all build upload install_local test speedtest profile annotate

# Real file rules

library_inputs := setup.py \
                  $(shell find streaming_form_data -maxdepth 1 -name "*.py") \
                  $(cython_file)

$(requirements_output): requirements.dev.txt
	pip install -r requirements.dev.txt
	@mkdir -p "$(@D)" && touch "$@"

$(install_local_output): $(requirements_output) $(library_inputs)
	pip install -e .
	@mkdir -p "$(@D)" && touch "$@"
