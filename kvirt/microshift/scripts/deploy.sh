{% if sslip %}
/root/scripts/00_sslip.sh
{% endif %}
/root/scripts/01_clients.sh
/root/scripts/02_crio.sh
/root/scripts/03_microshift.sh
{% if register_acm %}
/root/scripts/04_acm.sh
{% endif %}
