#!/bin/bash

for uuid in `ironic node-list | tail -4 | grep -v UUID| awk '{print $2}'` ; do
    #ironic node-update $uuid add properties/root_device='{"serial": "61866da04f37fc001ea4e31e121cfb45"}'
    ironic node-update ${uuid} add properties/root_device='{"name": "/dev/vda"}'
done

