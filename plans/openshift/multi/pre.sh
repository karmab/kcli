#!/usr/bin/env bash
yum -y install NetworkManager wget nc
[% if not crio %]
yum -y install docker
systemctl enable docker
systemctl start docker
[% endif %]
systemctl enable NetworkManager
systemctl start NetworkManager
yum -y update
[% if not deploy %]
reboot
[% endif %]
