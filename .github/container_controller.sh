#!/bin/bash

set -ex

cd extras/controller
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
docker build -t quay.io/karmab/kcli-controller:latest .

docker login -u $QUAY_USERNAME -p $QUAY_PASSWORD quay.io
docker push quay.io/karmab/kcli-controller:latest
