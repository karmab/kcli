blue='\033[0;36m'
clear='\033[0m'
echo -e "${blue}************ RUNNING 01_get_oc.sh ************${clear}"
bash /root/scripts/01_get_oc.sh
echo -e "${blue}************ RUNNING 03_registry.sh ************${clear}"
bash /root/scripts/03_registry.sh
{% if disconnected_sync %}
echo -e "${blue}************ RUNNING 03_mirror.sh ************${clear}"
bash /root/scripts/03_mirror.sh
echo -e "${blue}************ RUNNING 04_extras.sh ************${clear}"
bash /root/scripts/04_extras.sh
{% if disconnected_operators %}
echo -e "${blue}************ RUNNING 05_olm.sh ************${clear}"
bash /root/scripts/05_olm.sh
{% endif %}
{% endif %}
echo -e "${blue}************ RUNNING 06_web.sh ************${clear}"
bash /root/scripts/06_web.sh
