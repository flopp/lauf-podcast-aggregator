.PHONY: setup format run

setup:
	python3 -m venv venv
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install --upgrade -r requirements.txt
	./venv/bin/pip install --upgrade -r requirements-dev.txt

format:
	venv/bin/black py/*.py

lint:
	venv/bin/black --check py/*.py
	venv/bin/flake8 --max-line-length=90 py/*.py
	venv/bin/bandit --quiet py/*.py
	MYPYPATH=py venv/bin/mypy --strict py/*.py

run: setup
	./venv/bin/python py/main.py \
		--podcasts-json podcasts.json \
		--templates-dir templates \
		--export-dir .export \
		--cache-dir .cache
