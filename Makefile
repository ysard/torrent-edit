PACKAGE_NAME=torrent_edit

# Code formatting
black:
	black $(PACKAGE_NAME)

clean:
	rm -rf *.egg-info
	python setup.py clean --all

# development & release cycle
fullrelease:
	@# From zest.releaser
	fullrelease

install:
	@# Install a project in editable mode.
	pip install -e .[dev]

uninstall:
	pip uninstall $(PACKAGE_NAME)

sdist: clean
	@echo Building the distribution package...
	python -m build --sdist

wheel: clean
	@echo Building the wheel package...
	python -m build --wheel

upload:
	@echo Building the distribution + wheel packages...
	python -m build
	twine upload dist/* -r pypi

check_setups:
	pyroma .

check_code:
	prospector $(PACKAGE_NAME)/
	check-manifest
