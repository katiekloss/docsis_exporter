build:	env
	env/bin/pip install -r requirements.txt

env:
	python3 -m venv env
	env/bin/pip install --upgrade pip
