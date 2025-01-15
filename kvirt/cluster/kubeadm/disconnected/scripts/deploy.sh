blue='\033[0;36m'
clear='\033[0m'
echo -e "${blue}************ RUNNING 01_creds.sh ************${clear}"
bash /root/scripts/01_creds.sh
echo -e "${blue}************ RUNNING 02_packages.sh ************${clear}"
bash /root/scripts/02_packages.sh
echo -e "${blue}************ RUNNING 03_registry.sh ************${clear}"
bash /root/scripts/03_registry.sh
{% if disconnected_sync %}
echo -e "${blue}************ RUNNING 04_mirror.sh ************${clear}"
bash /root/scripts/04_mirror.sh
{% endif %}
echo -e "${blue}************ RUNNING 05_web.sh ************${clear}"
bash /root/scripts/05_web.sh
