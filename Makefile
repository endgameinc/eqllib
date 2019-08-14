#################
### EQL
#################

VENV := ./env/eqllib-build
VENV_BIN := $(VENV)/bin
PYTHON := $(VENV_BIN)/python
PIP := $(PYTHON) -m pip
SPHINXBUILD ?= $(VENV_BIN)/sphinx-build


$(VENV):
	pip install virtualenv
	virtualenv $(VENV)
	$(PIP) install setuptools -U
	$(PIP) install .
	$(PIP) install eqllib[test]

.PHONY: clean
clean:
	rm -rf $(VENV) *.egg-info .eggs *.egg htmlcov build dist .build .tmp .tox

.PHONY: pytest
pytest: $(VENV)
	$(PYTHON) setup.py -q test


.PHONY: test
test: $(VENV) pytest


.PHONY: sdist
sdist: $(VENV)
	$(PYTHON) setup.py sdist


.PHONY: bdist_egg
bdist_egg: $(VENV)
	$(PYTHON) setup.py bdist_egg


.PHONY: bdist_wheel
bdist_wheel: $(VENV)
	$(PYTHON) setup.py bdist_wheel


.PHONY: install
install: $(VENV) sdist
	$(PYTHON) setup.py install

.PHONY: all
all: sdist

.PHONY: docs
docs: $(VENV) install
	$(PIP) install eqllib[docs]
	cd docs && ../$(SPHINXBUILD) -M html . _build


.PHONY: upload
upload: $(VENV)
	$(PIP) install twine~=1.13
	$(VENV_BIN)/twine upload dist/*
