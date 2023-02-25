sleep 10
{% if odf_replicas == None %}
{% set odf_replicas = ctlplanes + workers %}
{% endif %}
{% if not odf_nodes %}
{% set odf_nodes = odf_replicas|defaultnodes(cluster, domain, ctlplanes,workers) %}
{% endif %}
{% if odf_nodes|length < odf_replicas %}
echo "Number of available nodes is lower than expected number of replicas"
exit 1
{% endif %}
{% for node in odf_nodes %}
oc label node {{ node }} cluster.ocs.openshift.io/openshift-storage=''
oc label node {{ node }} topology.rook.io/rack=rack{{ loop.index }}
{% endfor %}
