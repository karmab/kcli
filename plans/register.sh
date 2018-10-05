#!/usr/bin/env bash
sleep 10
subscription-manager register --force --username=ZZZ --password='ZZZ'
subscription-manager subscribe --pool=ZZZ
subscription-manager attach --auto
subscription-manager repos --disable="*"
subscription-manager repos --enable=rhel-7-server-rpms
