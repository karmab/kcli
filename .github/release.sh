#!/bin/bash

set -ex

"./cloudsmith_clean.sh"
"./cloudsmith.sh"
"./pypi.sh"
