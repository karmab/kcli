#!/bin/bash

sudo usermod -aG libvirt $(id -un)
sudo newgrp libvirt
