{% if ocs_default_storageclass %}
while true; do
  oc get sc/ocs-storagecluster-ceph-rbd 2>/dev/null && break;
  echo "Waiting for the storageclass to be created"
  sleep 5
done
 oc patch storageclass ocs-storagecluster-ceph-rbd -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
{% else %}
echo Run the following command to make ocs-storagecluster-ceph-rbd the default storage class
echo oc patch storageclass ocs-storagecluster-ceph-rbd -p \'{\"metadata\": {\"annotations\":{\"storageclass.kubernetes.io/is-default-class\":\"true\"}}}\'
{% endif %}

{% if ocs_public_network != None %}
oc create -f nad_public.yml
{% endif %}
{% if ocs_cluster_network != None %}
oc create -f nad_cluster.yml
{% endif %}
