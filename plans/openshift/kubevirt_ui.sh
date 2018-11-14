oc new-project kweb-ui
oc adm policy add-cluster-role-to-user cluster-admin system:serviceaccount:kweb-ui:default
oc apply -f kubevirt_ui.yml
