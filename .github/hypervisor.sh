#!/bin/bash

sudo systemctl start libvirt-bin
sudo usermod -aG qemu,libvirt $(id -un)
sudo newgrp libvirt
sudo systemctl start libvirt-bin
