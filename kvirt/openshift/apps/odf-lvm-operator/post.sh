{% if install_cr|default(True) %}
while true; do
  oc get sc/odf-lvm-{{ lvm_vg }} 2>/dev/null && break;
  echo "Waiting for the storageclass to be created"
  sleep 5
done
{% if lvm_default_storageclass %}
 oc patch storageclass odf-lvm-{{ lvm_vg }} -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
{% else %}
echo Run the following command to make localstorage the default storage class
echo oc patch storageclass odf-lvm-{{ lvm_vg }} -p \'{\"metadata\": {\"annotations\":{\"storageclass.kubernetes.io/is-default-class\":\"true\"}}}\'
{% endif %}
{% endif %}
