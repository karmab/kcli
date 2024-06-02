#!/bin/bash

find . -type f \( -iname "*.py" ! -iname "kcli_pb2*.py" ! -iname "bottle.py" \) -exec pycodestyle --ignore=E402,W504,E721,E722,E741 --max-line-length=120 {} +
find . -name '*.py' | misspellings -f -
