.PHONY: setup run

setup:
	python3 -m venv venv
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements.txt

run: setup
	./venv/bin/python py/main.py \
		--podcasts-json podcasts.json \
		--templates-dir templates \
		--export-dir .export
