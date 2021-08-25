.DEFAULT_GOAL := help
.PHONY := requirements

# Generates a help message. Borrowed from https://github.com/pydanny/cookiecutter-djangopackage
help: ## Display this help message
	@echo "Please use \`make <target>' where <target> is one of"
	@perl -nle'print $& if m{^[\.a-zA-Z_-]+:.*?## .*$$}' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m  %-25s\033[0m %s\n", $$1, $$2}'

requirements:
	pip install -r requirements/base.txt

upgrade: ## update the pip requirements files to use the latest releases satisfying our constraints
	docker-compose build && docker-compose run hermes make upgrade-requirements

upgrade-requirements: export CUSTOM_COMPILE_COMMAND=make upgrade
upgrade-requirements: ## update the pip requirements files to use the latest releases satisfying our constraints
	pip install -q -r requirements/pip_tools.txt
	pip-compile --upgrade -o requirements/pip_tools.txt requirements/pip_tools.in
	pip-compile --upgrade -o requirements/base.txt requirements/base.in
