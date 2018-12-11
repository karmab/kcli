KUBEVIRT_UI="{{ ui_version }}"
kubectl create namespace kweb-ui
kubectl create clusterrolebinding kweb-ui --clusterrole=edit --user=system:serviceaccount:kweb-ui:default
sed -i "s/KUBEVIRT_UI/$KUBEVIRT_UI/" /root/kubevirt_ui.yml
kubectl create -f /root/kubevirt_ui.yml -n kweb-ui
