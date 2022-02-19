#!/bin/bash

set -ex

".github/cloudsmith_clean.sh"
".github/cloudsmith.sh"
".github/pypi.sh"
