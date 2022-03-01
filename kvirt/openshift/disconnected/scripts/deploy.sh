bash /root/scripts/01_get_oc.sh
bash /root/scripts/03_registry.sh
bash /root/scripts/03_mirror.sh
bash /root/scripts/04_extras.sh
{% if disconnected_operators %}
bash /root/scripts/05_olm.sh
{% endif %}
bash /root/scripts/06_web.sh
