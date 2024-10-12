#!/bin/bash

IGNORE_LIST="aks"
find kvirt -type f \( -iname "*.py" ! -iname "bottle.py" \) -exec pycodestyle --ignore=E402,W504,E721,E722,E741 --max-line-length=120 {} +
find . -name '*.py' | codespell -f - -L "$IGNORE_LIST"
