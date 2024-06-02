#!/bin/bash

export VERSION=$(date "+%Y%m%d%H%M")
sed -i "s/99.0/99.0.$VERSION/" setup_kfish.py
rm -rf build dist
mv setup_kfish.py setup.py
python3 -m build
pip3 install twine
twine upload --repository-url https://upload.pypi.org/legacy/ -u $PYPI_USERNAME -p $PYPI_PASSWORD --skip-existing dist/*
