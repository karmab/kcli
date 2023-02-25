#!/usr/bin/env bash

export PATH=/root:$PATH
test -f /etc/profile.d/kcli.sh && source /etc/profile.d/kcli.sh
{% if config_type == 'gcp' %}
systemctl enable --now gcp-hack
{% endif %}
pre.sh
{% if eksd %}
eksd.sh
{% endif %}
{% if config_type not in ['aws', 'gcp', 'ibm'] %}
keepalived.sh
{% endif %}
ctlplanes.sh
