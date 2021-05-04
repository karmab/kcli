echo Run the following command to make ocs your default storage class
echo oc patch storageclass ocs-storagecluster-ceph-rbd -p \'{\"metadata\": {\"annotations\":{\"storageclass.kubernetes.io/is-default-class\":\"true\"}}}\'
