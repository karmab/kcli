#!/bin/bash

set -ex

".github/copr.sh"
".github/cloudsmith_clean.sh"
".github/cloudsmith.sh"
".github/pypi.sh"
