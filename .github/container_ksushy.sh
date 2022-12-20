#!/bin/bash

set -ex

cd extras/ksushy

git clone https://github.com/openshift-metal3/fakefish
mv fakefish/* .
podman build -t quay.io/karmab/ksushy:latest .
podman login -u $QUAY_USERNAME -p $QUAY_PASSWORD quay.io
podman push quay.io/karmab/ksushy:latest
