kubectl create namespace kweb-ui
kubectl create clusterrolebinding kweb-ui --clusterrole=edit --user=system:serviceaccount:kweb-ui:default
kubectl create -f /root/kubevirt_ui.yml -n kweb-ui
