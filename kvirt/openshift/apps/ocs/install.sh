{%- if not ocs_nodes %}
{%- set ocs_nodes = [] %}
{%- for num in range(0, workers) %}
{%- if ocs_nodes|length < replicas %}
{%- do ocs_nodes.append("%s-worker-%s.%s.%s" % (cluster, num|string, cluster, domain)) %}
{% endif %}
{%- endfor %}
{%- for num in range(0, masters) %}
{%- if ocs_nodes|length < replicas %}
{%- do ocs_nodes.append("%s-master-%s.%s.%s" % (cluster, num|string, cluster, domain)) %}
{%- endif %}
{%- endfor %}
{%- endif %}
{%- if ocs_nodes|length < replicas %}
echo "Number of available nodes is lower than expected number of replicas"
exit 1
{%- endif %}
{%- for node in ocs_nodes %}
oc label {{ node }} cluster.ocs.openshift.io/openshift-storage=''
oc label node {{ node }} topology.rook.io/rack=rack{{ loop.index }}
{%- endfor %}
oc create -f install.yml
sleep 10
oc wait --for=condition=Ready pod -l name=ocs-operator -n openshift-storage
oc create -f cr.yml
oc patch storageclass ocs-storagecluster-cephfs -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
oc patch OCSInitialization ocsinit -n openshift-storage --type json --patch  '[{ "op": "replace", "path": "/spec/enableCephTools", "value": true }]'
