#!/bin/bash
export VERSION=$(date "+%Y%m%d%H%M")
sed -i "s/99.0/99.0.$VERSION/" setup.py
python3 setup.py bdist_wheel
pip3 install twine
twine upload --repository-url https://upload.pypi.org/legacy/ -u $PYPI_USERNAME -p $PYPI_PASSWORD --skip-existing dist/*
