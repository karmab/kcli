#!/bin/bash

cd extras/controller

curl -LO "https://cdn.dl.k8s.io/release/$(curl -L -s https://cdn.dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
podman build -t quay.io/karmab/kcli-controller:latest .
podman login -u $QUAY_USERNAME -p $QUAY_PASSWORD quay.io
podman push quay.io/karmab/kcli-controller:latest

#curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
#podman build --arch=amd64 -t quay.io/karmab/kcli-controller:amd64 .
#curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/arm64/kubectl"
#podman build --arch=arm64 -t quay.io/karmab/kcli-controller:arm64 .
#podman login -u $QUAY_USERNAME -p $QUAY_PASSWORD quay.io
#podman manifest create quay.io/karmab/kcli-controller:latest
#podman manifest add quay.io/karmab/kcli-controller:latest docker://quay.io/karmab/kcli-controller:amd64
#podman manifest add quay.io/karmab/kcli-controller:latest docker://quay.io/karmab/kcli-controller:arm64
#podman manifest push --all quay.io/karmab/kcli-controller:latest  docker://quay.io/karmab/kcli-controller:latest
