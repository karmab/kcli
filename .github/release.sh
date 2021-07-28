#!/bin/bash

set -ex

docker login -u $QUAY_USERNAME -p $QUAY_PASSWORD quay.io
docker push quay.io/karmab/kcli:latest

"./cloudsmith_clean.sh"
"./cloudsmith.sh"
"./pypi.sh"
