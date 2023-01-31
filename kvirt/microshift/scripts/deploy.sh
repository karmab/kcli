{% set client_script = '01_clients.sh' if 'rhel' in image else '01_clients_upstream.sh' %}
{% set crio_script = '02_crio.sh' if 'rhel' in image else '02_crio_upstream.sh' %}
{% set microshift_script = '03_microshift.sh' if 'rhel' in image else '03_microshift_upstream.sh' %}
blue='\033[0;36m'
clear='\033[0m'

{% if sslip %}
echo -e "${blue}************ RUNNING 00_sslip.sh ************${clear}"
/root/scripts/00_sslip.sh
{% endif %}
echo -e "${blue}************ RUNNING {{ client_script}} ************${clear}"
/root/scripts/{{ client_script }}
echo -e "${blue}************ RUNNING {{ crio_script }} ************${clear}"
/root/scripts/{{ crio_script }}
echo -e "${blue}************ RUNNING {{ microshift_script }} ************${clear}"
/root/scripts/{{ microshift_script }}
echo -e "${blue}************ RUNNING 04_kubeconfig.sh ************${clear}"
/root/scripts/04_kubeconfig.sh
{% if register_acm %}
echo -e "${blue}************ RUNNING 05_acm.sh ************${clear}"
/root/scripts/05_acm.sh
{% endif %}
