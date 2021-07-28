#!/bin/bash

set -ex

docker login -u $QUAY_USERNAME -p $QUAY_PASSWORD quay.io
docker push quay.io/karmab/kcli:latest

#"./cloudsmith.sh"
#"./cloudsmith_clean.sh"
"./pypi.sh"
