SHELL := /bin/bash

define activate =
source env/bin/activate
endef

# Only run install if requirements.txt is newer than SITE_PACKAGES location
.PHONY: install
SITE_PACKAGES := $(shell pip show pip | grep '^Location' | cut -f2 -d':')
install: env $(SITE_PACKAGES)

$(SITE_PACKAGES): requirements.txt
	$(activate)
	pip install -r requirements.txt

env:
	python3 -m venv env

lint: install
	$(activate)
	pylint -v docsis_exporter.py
