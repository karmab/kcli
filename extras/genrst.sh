#!/bin/bash
# brew install pandoc
file="index.md"
pandoc --from=markdown --to=rst $file -o ${file%.*}.rst
