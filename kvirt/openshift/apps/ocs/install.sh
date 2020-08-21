{%- if ocs_nodes %}
{%- for node in ocs_nodes %}
OCS_NODE={{ node }}
oc label $OCS_NODE cluster.ocs.openshift.io/openshift-storage=''
oc label node $OCS_NODE topology.rook.io/rack=rack{{ loop.index }}
{%- endfor %}
{%- else %}
{%- for num in range(masters) %}
OCS_NODE={{ cluster }}.master-{{ num }}.{{ cluster }}.{{ domain }}
oc label $OCS_NODE cluster.ocs.openshift.io/openshift-storage=''
oc label node $OCS_NODE topology.rook.io/rack=rack{{ num }}
{%- endfor %}
{%- endif %}
oc create -f install.yml
sleep 10
oc wait --for=condition=Ready pod -l name=ocs-operator -n openshift-storage
oc create -f cr.yml
oc patch storageclass ocs-storagecluster-cephfs -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
oc patch OCSInitialization ocsinit -n openshift-storage --type json --patch  '[{ "op": "replace", "path": "/spec/enableCephTools", "value": true }]'
