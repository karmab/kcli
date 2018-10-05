#!/usr/bin/env bash
subscription-manager repos --enable=rhel-6-server-rpms --enable=rhel-6-server-supplementary-rpms --enable=rhel-6-server-rhevm-[[ version ]]-rpms --enable=jb-eap-6-for-rhel-6-server-rpms --enable=rhel-6-server-rhev-mgmt-agent-rpms
