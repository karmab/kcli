oc new-project kweb-ui
oc apply -f kubevirt-web-ui.yaml
oc adm policy add-cluster-role-to-user cluster-admin system:serviceaccount:kweb-ui:default
