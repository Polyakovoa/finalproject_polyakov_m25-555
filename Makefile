install:
	poetry install

project:
	poetry run python main.py

build:
	poetry build

publish:
	poetry publish --dry-run

package-install:
	pip install dist/*.whl

lint:
	poetry run ruff check .

lint-fix:
	poetry run ruff check . --fix

format:
	poetry run ruff format .