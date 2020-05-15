#!/bin/bash

set -ex

git rev-parse --short HEAD > kvirt/version/git
docker build -t karmab/kcli -f extras/alpine .
