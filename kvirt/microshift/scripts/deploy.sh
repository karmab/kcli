blue='\033[0;36m'
clear='\033[0m'

{% if sslip %}
echo -e "${blue}************ RUNNING 00_sslip.sh ************${clear}"
/root/scripts/00_sslip.sh
{% endif %}
echo -e "${blue}************ RUNNING 01_clients.sh ************${clear}"
/root/scripts/01_clients.sh
echo -e "${blue}************ RUNNING 02_crio.sh ************${clear}"
/root/scripts/02_crio.sh
echo -e "${blue}************ RUNNING 03_microshift.sh ************${clear}"
/root/scripts/03_microshift.sh
echo -e "${blue}************ RUNNING 04_kubeconfig.sh ************${clear}"
/root/scripts/04_kubeconfig.sh
{% if register_acm %}
echo -e "${blue}************ RUNNING 05_acm.sh ************${clear}"
/root/scripts/05_acm.sh
{% endif %}
