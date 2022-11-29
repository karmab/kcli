#!/bin/bash

set -ex

cd extras/controller
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
podman build -t quay.io/karmab/kcli-controller:latest .

podman login -u $QUAY_USERNAME -p $QUAY_PASSWORD quay.io
podman push quay.io/karmab/kcli-controller:latest
