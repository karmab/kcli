{% if sriov_kvm %}
oc patch configmap supported-nic-ids -n openshift-sriov-network-operator --type merge -p '{"data":{"Intel_igb_82576":"8086 10c9 10ca"}}'
oc patch configmap supported-nic-ids -n openshift-sriov-network-operator --type merge -p '{"data":{"Intel_ixgbe_10G_X550":"8086 1563 1565"}}'
{% endif %}
