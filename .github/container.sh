#!/bin/bash

set -ex

TAG="$(git rev-parse --short HEAD)"
GIT_VERSION="$TAG $(date +%Y/%m/%d)"
echo $GIT_VERSION > kvirt/version/git
podman build --arch=amd64 -t quay.io/karmab/kcli:amd64 -f extras/debian .
podman build --arch=arm64 -t quay.io/karmab/kcli:arm64 -f extras/debian .

podman images
podman manifest create quay.io/karmab/kcli:latest
podman manifest add quay.io/karmab/kcli:latest docker://quay.io/karmab/kcli:amd64
podman manifest add quay.io/karmab/kcli:latest docker://quay.io/karmab/kcli:arm64
podman login -u $QUAY_USERNAME -p $QUAY_PASSWORD quay.io
podman manifest push --all quay.io/karmab/kcli:latest docker://quay.io/karmab/kcli:latest
