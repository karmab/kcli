#!/bin/bash

find . -type f -exec sed -i -e 's/\[\[/{{/' -e 's/\]\]/}}/' -e 's/\[%/{%/' -e 's/%\]/%}/'  {} +
