SHELL := /bin/bash

build:	env
	pip install -r requirements.txt

env:
	python3 -m venv env
	source env/bin/activate
	pip install --upgrade pip
