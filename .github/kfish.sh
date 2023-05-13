#!/bin/bash

set -ex

export VERSION=$(date "+%Y%m%d%H%M")
sed -i "s/99.0/99.0.$VERSION/" setup_kfish.py
rm -rf build dist
python setup_kfish.py bdist_wheel
pip3 install twine
twine upload --repository-url https://upload.pypi.org/legacy/ -u $PYPI_USERNAME -p $PYPI_PASSWORD --skip-existing dist/*
