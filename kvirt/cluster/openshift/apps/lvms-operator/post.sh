{% if install_cr|default(True) %}
while true; do
  oc get sc/lvms-{{ lvms_vg }} 2>/dev/null && break;
  echo "Waiting for the storageclass to be created"
  sleep 5
done
{% if not lvms_default_storageclass %}
echo Run the following command to make localstorage the default storage class
echo "oc patch lvmcluster lvmcluster -n openshift-lvm-storage --type json -p '[{\"op\":\"add\",\"path\":\"/spec/storage/deviceClasses/0/default\",\"value\":true}]'"
{% endif %}
{% endif %}
