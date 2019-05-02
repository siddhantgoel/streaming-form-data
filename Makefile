BLACK=black
POETRY=poetry run

cython-file := streaming_form_data/_parser.pyx

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf streaming_form_data.egg-info

#
# Development
#

annotate:
	$(POETRY) cython -a $(cython-file) -o build/annotation.html

compile:
	$(POETRY) cython $(cython-file)

black:
	$(POETRY) $(BLACK) streaming_form_data/*.py tests/ utils/ examples/**/*.py build.py

#
# Utils
#

speed-test:
	$(POETRY) python utils/speedtest.py

profile:
	$(POETRY) python utils/profile.py --data-size 17555000 -c binary/octet-stream

.PHONY: clean \
	annotate compile \
	speed-test profile
