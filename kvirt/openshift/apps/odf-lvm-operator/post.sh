oc adm policy add-cluster-role-to-user cluster-admin -z vg-manager -n odf-lvm
oc adm policy add-cluster-role-to-user cluster-admin -z topolvm-controller -n odf-lvm
oc adm policy add-cluster-role-to-user cluster-admin -z topolvm-node -n odf-lvm
