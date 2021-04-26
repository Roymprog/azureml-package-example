# include .env.template
# export $(shell sed 's/=.*//' .env.template)

# ifeq ("$(shell test -e .env && echo exists)", "exists")
# 	include .env
# 	export $(shell sed 's/=.*//' .env)
# endif

.DEFAULT_GOAL := help

define BROWSER_PYSCRIPT
import os, webbrowser, sys

try:
	from urllib import pathname2url
except:
	from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

BROWSER := python -c "$$BROWSER_PYSCRIPT"

.PHONY: help
help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

.PHONY: clean
clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts

.PHONY: clean-build
clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

.PHONY: clean-pyc
clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

.PHONY: clean-test
clean-test: ## remove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage coverage.xml
	rm -fr htmlcov/
	rm -fr .pytest_cache

.PHONY: dist
dist: clean ## Builds source and wheel package.
	python -m pep517.build .
	ls -l dist

.PHONY: env
env: ## create conda env
	conda env create --file environment.yml

.PHONY: lint
lint: ## check style with pylint
	python -m pylint model/my_package model/scripts/*.py

.PHONY: test
test: ## run tests with the default Python
	PYTHONPATH=model python -m pytest tests \
	 	--junitxml=.junit/test-results.xml \
	 	--cov=my_package \
	 	--cov-report=html \
	 	--cov-report=xml \
	 	--cov-report=term

.PHONY: test-installed
test-installed: ## run tests on installed package
	PYTHONPATH= python -m pytest tests \
		--junitxml=.junit/test-results.xml \
		--cov=my_package \
		--cov-report=html \
		--cov-report=xml \
		--cov-report=term

.PHONY: pre-commit
pre-commit:
	pre-commit run --all
