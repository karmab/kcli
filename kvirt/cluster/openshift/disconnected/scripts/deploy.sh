blue='\033[0;36m'
clear='\033[0m'
echo -e "${blue}************ RUNNING 01_packages.sh ************${clear}"
bash /root/scripts/01_packages.sh
echo -e "${blue}************ RUNNING 02_registry.sh ************${clear}"
bash /root/scripts/02_registry.sh
{% if disconnected_sync %}
echo -e "${blue}************ RUNNING 03_mirror.sh ************${clear}"
bash /root/scripts/03_mirror.sh
{% endif %}
echo -e "${blue}************ RUNNING 04_web.sh ************${clear}"
bash /root/scripts/04_web.sh
