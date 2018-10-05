#!/usr/bin/env bash
subscription-manager repos --enable=rhel-7-server-supplementary-rpms --enable=rhel-7-server-rhv-[[ version ]]-rpms --enable=jb-eap-7-for-rhel-7-server-rpms --enable=rhel-7-server-rhv-4-mgmt-agent-rpms
