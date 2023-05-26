#!/usr/bin/env bash

export PATH=/root:$PATH
test -f /etc/profile.d/kcli.sh && source /etc/profile.d/kcli.sh
pre.sh
{% if config_type not in ['aws', 'gcp', 'ibm'] and '%s-ctlplane' % cluster in name %}
keepalived.sh
{% endif %}

{% set deploy_script = 'bootstrap.sh' if '%s-ctlplane-0' % cluster in name else 'join.sh' %}

{{ deploy_script }}
