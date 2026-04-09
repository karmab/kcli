#!/bin/bash

TAG="$(git rev-parse --short HEAD)"
GIT_VERSION="$TAG $(date +%Y/%m/%d)"
echo $GIT_VERSION > kvirt/version/git

podman login -u $QUAY_USERNAME -p $QUAY_PASSWORD quay.io
podman build -t quay.io/karmab/kcli:latest -f extras/Dockerfile .
podman push quay.io/karmab/kcli:latest
