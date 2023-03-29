style:
	poetry run isort -c .
	poetry run flake8
	poetry run mypy

test:
	poetry run coverage run
	poetry run coverage report

publish:
	poetry publish --build
