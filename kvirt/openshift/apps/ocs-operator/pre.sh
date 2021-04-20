sleep 10
{% if ocs_replicas == None %}
{% set ocs_replicas = masters + workers %}
{% endif %}
{% if not ocs_nodes %}
{% set ocs_nodes = ocs_replicas|defaultnodes(cluster, domain, masters,workers) %}
{% endif %}
{% if ocs_nodes|length < ocs_replicas %}
echo "Number of available nodes is lower than expected number of replicas"
exit 1
{% endif %}
{% for node in ocs_nodes %}
oc label node {{ node }} cluster.ocs.openshift.io/openshift-storage=''
oc label node {{ node }} topology.rook.io/rack=rack{{ loop.index }}
{% endfor %}
