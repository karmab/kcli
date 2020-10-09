oc create -f install.yml
{% if not ocs_deploycluster %}
exit
{% endif %}
sleep 10
{%- if ocs_replicas == None %}
{%- set ocs_replicas = masters + workers %}
{%- endif %}
{%- if not ocs_nodes %}
{%- set ocs_nodes = ocs_replicas|defaultnodes(cluster, domain, masters,workers) %}
{%- endif %}
{%- if ocs_nodes|length < ocs_replicas %}
echo "Number of available nodes is lower than expected number of replicas"
exit 1
{%- endif %}
{%- for node in ocs_nodes %}
oc label node {{ node }} cluster.ocs.openshift.io/openshift-storage=''
oc label node {{ node }} topology.rook.io/rack=rack{{ loop.index }}
{%- endfor %}
oc wait --for=condition=Ready pod -l name=ocs-operator -n openshift-storage
{{ 'storagecluster'| waitcrd }}
oc create -f cr.yml
echo Run the following command to make ocs your default storage class
# oc patch storageclass ocs-storagecluster-ceph-rbd -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
echo oc patch storageclass ocs-storagecluster-ceph-rbd -p \'{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}\'
# oc patch OCSInitialization ocsinit -n openshift-storage --type json --patch  '[{ "op": "replace", "path": "/spec/enableCephTools", "value": true }]'
