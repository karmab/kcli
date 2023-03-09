{% if install_cr|default(True) %}
while true; do
  oc get sc/lvms-{{ lvms_vg }} 2>/dev/null && break;
  echo "Waiting for the storageclass to be created"
  sleep 5
done
{% if lvms_default_storageclass %}
 oc patch storageclass lvms-{{ lvms_vg }} -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
{% else %}
echo Run the following command to make localstorage the default storage class
echo oc patch storageclass lvms-{{ lvms_vg }} -p \'{\"metadata\": {\"annotations\":{\"storageclass.kubernetes.io/is-default-class\":\"true\"}}}\'
{% endif %}
{% endif %}
