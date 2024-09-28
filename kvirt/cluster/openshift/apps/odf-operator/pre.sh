{% if odf_nodes %}
{% set nodes = odf_nodes %}
{% elif localstorage_nodes is defined %}
{% set nodes = localstorage_nodes %}
{% else %}
{% set nodes = odf_replicas|defaultnodes(cluster, domain, ctlplanes, workers) %}
{% endif %}

{% if nodes|length < odf_replicas %}
echo "Number of available nodes is lower than expected number of replicas"
exit 1
{% endif %}

{% if nodes|has_ctlplane %}
echo "Marking all ctlplane nodes as schedulable since one of them will be used for storage"
oc patch scheduler cluster -p '{"spec":{"mastersSchedulable": true}}' --type merge
{% endif %}


{% for node in nodes %}
oc label node {{ node }} cluster.ocs.openshift.io/openshift-storage=''
oc label node {{ node }} topology.rook.io/rack=rack{{ loop.index }}
{% endfor %}
