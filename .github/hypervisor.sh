#!/bin/bash

sudo usermod -aG qemu,libvirt $(id -un)
sudo newgrp libvirt
