#!/bin/bash

set -ex

git rev-parse --short HEAD > kvirt/version/git
docker build -t quay.io/karmab/kcli -f extras/alpine .
