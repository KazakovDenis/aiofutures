style:
	poetry run isort -c .
	poetry run flake8

test:
	poetry run coverage run
	poetry run coverage report
